"""Deterministic structure-aware chunking over normalization output."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

from ragscanner.chunking.models import (
    ChunkingConfig,
    ChunkingError,
    ChunkingErrorCategory,
    ChunkingResult,
    ChunkingStatistics,
    ChunkingStrategy,
    ChunkingWarning,
    TokenCounter,
)
from ragscanner.chunking.tokenizer import WhitespaceTokenCounter
from ragscanner.domain import Chunk, Document, SourceLocation
from ragscanner.domain.helpers import document_content_hash
from ragscanner.normalization import AnnotationType, NormalizationAnnotation, NormalizationResult

_PARAGRAPH_END = re.compile(r"\n[ \t]*\n+")
_SENTENCE_END = re.compile(r"[.!?](?:[\"')\]]+)?\s+")


@dataclass(slots=True)
class _Block:
    start: int
    end: int
    block_types: set[str] = field(default_factory=set)
    heading_path: list[str] = field(default_factory=list)
    pages: set[int] = field(default_factory=set)
    sections: set[str] = field(default_factory=set)
    parser_blocks: set[int] = field(default_factory=set)
    approximate: bool = False
    forced_split: bool = False


@dataclass(slots=True)
class _ChunkSpan:
    start: int
    end: int
    blocks: list[_Block]
    overlap_start: int | None = None


class DocumentChunker:
    """Create stable Chunk models without mutating document or normalization output."""

    name = "document_chunker"
    version = "1.1.0"

    def __init__(
        self,
        config: ChunkingConfig | None = None,
        tokenizer: TokenCounter | None = None,
    ) -> None:
        self.config = config or ChunkingConfig()
        self.tokenizer = tokenizer or WhitespaceTokenCounter()

    def chunk(self, document: Document, normalized: NormalizationResult) -> ChunkingResult:
        self._validate(document, normalized)
        text = normalized.normalized_content
        warnings = [
            ChunkingWarning(
                code="tokenizer_approximation",
                message="Token counts use a deterministic model-independent approximation.",
                metadata={"tokenizer": self.tokenizer.name, "version": self.tokenizer.version},
            )
        ]
        if not text:
            warnings.append(
                ChunkingWarning(
                    code="empty_normalized_document",
                    message="The normalized document is empty; no chunks were created.",
                )
            )
            return self._result(document, normalized, [], warnings, 0, 0, 0)
        blocks = self._blocks(text, normalized)
        if len(blocks) > self.config.maximum_blocks:
            raise ChunkingError(
                ChunkingErrorCategory.BLOCK_LIMIT_EXCEEDED,
                "document exceeds configured structural block limit",
            )
        expanded: list[_Block] = []
        forced_splits = 0
        for block in blocks:
            split = self._split_large_block(text, block, warnings)
            forced_splits += max(0, len(split) - 1)
            expanded.extend(split)
        spans = self._pack(text, expanded)
        spans = self._apply_overlap(text, spans, warnings)
        if len(spans) > self.config.maximum_chunks_per_document:
            raise ChunkingError(
                ChunkingErrorCategory.MAXIMUM_CHUNKS_REACHED,
                "chunking would exceed maximum chunks; no partial result was returned",
            )
        chunks = [
            self._chunk_model(document, normalized, span, index, warnings)
            for index, span in enumerate(spans)
        ]
        overlap_tokens = sum(
            self.tokenizer.count(text[span.start : span.overlap_start])
            for span in spans
            if span.overlap_start is not None and span.overlap_start > span.start
        )
        approximate = sum(
            bool(chunk.metadata.get("approximate_source_mapping")) for chunk in chunks
        )
        for chunk in chunks:
            if chunk.token_count < self.config.minimum_token_count:
                warnings.append(
                    ChunkingWarning(
                        code="undersized_chunk",
                        message="A chunk is below the configured minimum token target.",
                        normalized_start=int(chunk.metadata["normalized_start"]),
                        normalized_end=int(chunk.metadata["normalized_end"]),
                    )
                )
        return self._result(
            document,
            normalized,
            chunks,
            warnings,
            len(expanded),
            forced_splits,
            overlap_tokens,
            approximate,
        )

    def _validate(self, document: Document, normalized: NormalizationResult) -> None:
        if (
            normalized.document_id != document.id
            or normalized.original_hash != document.content_hash
        ):
            raise ChunkingError(
                ChunkingErrorCategory.INVALID_INPUT,
                "normalization result does not belong to the supplied document",
            )
        if document_content_hash(normalized.normalized_content) != normalized.normalized_hash:
            raise ChunkingError(
                ChunkingErrorCategory.INVALID_INPUT,
                "normalized content hash is invalid",
            )
        if len(normalized.normalized_content) > self.config.maximum_input_characters:
            raise ChunkingError(
                ChunkingErrorCategory.INPUT_LIMIT_EXCEEDED,
                "normalized input exceeds configured character limit",
            )

    def _blocks(self, text: str, normalized: NormalizationResult) -> list[_Block]:
        if self.config.strategy is ChunkingStrategy.TOKEN_WINDOW:
            return [self._enrich(_Block(0, len(text)), normalized)]
        boundaries = {0, len(text)}
        for match in _PARAGRAPH_END.finditer(text):
            boundaries.add(match.end())
        if self.config.strategy is ChunkingStrategy.STRUCTURE_AWARE:
            for start, end in self._structural_ranges(text, normalized.annotations):
                boundaries.add(start)
                boundaries.add(end)
            if self.config.preserve_page_boundaries:
                previous_page: int | None = None
                for segment in normalized.segments:
                    page = segment.source_location.page_number
                    if page is not None and previous_page is not None and page != previous_page:
                        boundaries.add(segment.normalized_start)
                    if page is not None:
                        previous_page = page
        ordered = sorted(value for value in boundaries if 0 <= value <= len(text))
        blocks = [
            self._enrich(_Block(start, end), normalized)
            for start, end in pairwise(ordered)
            if end > start
        ]
        enriched = self._heading_paths(text, blocks, normalized.annotations)
        return self._attach_nonsemantic_blocks(text, enriched)

    def _attach_nonsemantic_blocks(self, text: str, blocks: list[_Block]) -> list[_Block]:
        """Keep delimiters and whitespace with nearby content instead of indexing them alone."""
        if not blocks or not any(self._has_semantic_content(text, block) for block in blocks):
            return blocks
        result: list[_Block] = []
        leading: list[_Block] = []
        for block in blocks:
            if self._has_semantic_content(text, block):
                if leading:
                    block = self._combined_block([*leading, block], heading_path=block.heading_path)
                    leading = []
                result.append(block)
            elif result:
                result[-1] = self._combined_block(
                    [result[-1], block], heading_path=result[-1].heading_path
                )
            else:
                leading.append(block)
        return result

    @staticmethod
    def _has_semantic_content(text: str, block: _Block) -> bool:
        return any(character.isalnum() for character in text[block.start : block.end])

    @staticmethod
    def _combined_block(blocks: list[_Block], *, heading_path: list[str]) -> _Block:
        return _Block(
            start=blocks[0].start,
            end=blocks[-1].end,
            block_types={kind for block in blocks for kind in block.block_types},
            heading_path=list(heading_path),
            pages={page for block in blocks for page in block.pages},
            sections={section for block in blocks for section in block.sections},
            parser_blocks={value for block in blocks for value in block.parser_blocks},
            approximate=any(block.approximate for block in blocks),
            forced_split=any(block.forced_split for block in blocks),
        )

    def _structural_ranges(
        self, text: str, annotations: list[NormalizationAnnotation]
    ) -> list[tuple[int, int]]:
        protected_types = {
            AnnotationType.LIST_REGION,
            AnnotationType.TABLE_REGION,
            AnnotationType.CODE_REGION,
        }
        ranges: list[tuple[int, int]] = []
        for annotation_type in protected_types:
            selected = sorted(
                (item for item in annotations if item.annotation_type is annotation_type),
                key=lambda item: (item.normalized_start, item.normalized_end),
            )
            if not selected:
                continue
            start, end = selected[0].normalized_start, selected[0].normalized_end
            for annotation in selected[1:]:
                gap = text[end : annotation.normalized_start]
                if not gap.strip():
                    end = max(end, annotation.normalized_end)
                else:
                    ranges.append((start, end))
                    start, end = annotation.normalized_start, annotation.normalized_end
            ranges.append((start, end))
        singular = {
            AnnotationType.HEADING_REGION,
            AnnotationType.PAGE_BOUNDARY,
            AnnotationType.SECTION_BOUNDARY,
            AnnotationType.HEADER_REGION,
            AnnotationType.FOOTER_REGION,
        }
        for annotation in annotations:
            if annotation.annotation_type not in singular:
                continue
            value = text[annotation.normalized_start : annotation.normalized_end]
            if "RAGSCANNER_PAGE_BOUNDARY" in value and not self.config.preserve_page_boundaries:
                continue
            ranges.append((annotation.normalized_start, annotation.normalized_end))
        return sorted(set(ranges))

    def _enrich(self, block: _Block, normalized: NormalizationResult) -> _Block:
        for annotation in normalized.annotations:
            if self._intersects(
                block.start, block.end, annotation.normalized_start, annotation.normalized_end
            ):
                block.block_types.add(annotation.annotation_type.value)
        for segment in normalized.segments:
            if not self._intersects(
                block.start, block.end, segment.normalized_start, segment.normalized_end
            ):
                continue
            if segment.source_location.page_number is not None:
                block.pages.add(segment.source_location.page_number)
            if segment.source_location.section is not None:
                block.sections.add(segment.source_location.section)
            parser_block = segment.metadata.get("parser_block")
            if isinstance(parser_block, int):
                block.parser_blocks.add(parser_block)
            block.approximate = block.approximate or segment.approximate
        return block

    def _heading_paths(
        self,
        text: str,
        blocks: list[_Block],
        annotations: list[NormalizationAnnotation],
    ) -> list[_Block]:
        heading_by_range: dict[tuple[int, int], NormalizationAnnotation] = {}
        for annotation in annotations:
            if annotation.annotation_type is not AnnotationType.HEADING_REGION:
                continue
            if (
                "RAGSCANNER_PAGE_BOUNDARY"
                in text[annotation.normalized_start : annotation.normalized_end]
            ):
                continue
            key = (annotation.normalized_start, annotation.normalized_end)
            existing = heading_by_range.get(key)
            if existing is None or (
                "level" in annotation.metadata and "level" not in existing.metadata
            ):
                heading_by_range[key] = annotation
        headings = sorted(
            heading_by_range.values(),
            key=lambda item: (item.normalized_start, item.normalized_end),
        )
        path: list[str] = []
        heading_index = 0
        for block in blocks:
            while (
                heading_index < len(headings)
                and headings[heading_index].normalized_start <= block.start
            ):
                heading = headings[heading_index]
                level = heading.metadata.get("level", 1)
                level = level if isinstance(level, int) and 1 <= level <= 9 else 1
                value = text[heading.normalized_start : heading.normalized_end].strip()
                if value:
                    path = path[: level - 1]
                    path.append(value)
                heading_index += 1
            block.heading_path = list(path)
        return blocks

    def _split_large_block(
        self, text: str, block: _Block, warnings: list[ChunkingWarning]
    ) -> list[_Block]:
        value = text[block.start : block.end]
        if self._within_limit(value):
            return [block]
        types = block.block_types
        is_table = AnnotationType.TABLE_REGION.value in types
        is_code = AnnotationType.CODE_REGION.value in types
        is_list = AnnotationType.LIST_REGION.value in types
        warning_code = "oversized_block"
        if is_table:
            warning_code = "table_split"
        elif is_code:
            warning_code = "code_block_split"
        elif is_list:
            warning_code = "list_split"
        warnings.append(
            ChunkingWarning(
                code=warning_code,
                message="A structural block exceeded limits and required a conservative split.",
                normalized_start=block.start,
                normalized_end=block.end,
                metadata={"block_types": sorted(types)},
            )
        )
        boundaries = self._safe_split_boundaries(value)
        result: list[_Block] = []
        cursor = 0
        while cursor < len(value):
            end = self._maximum_end(value, cursor)
            candidates = [point for point in boundaries if cursor < point <= end]
            chosen = max(candidates) if candidates else end
            if chosen <= cursor:
                chosen = min(len(value), cursor + self.config.maximum_characters)
            child = _Block(
                start=block.start + cursor,
                end=block.start + chosen,
                block_types=set(block.block_types),
                heading_path=list(block.heading_path),
                pages=set(block.pages),
                sections=set(block.sections),
                parser_blocks=set(block.parser_blocks),
                approximate=block.approximate,
                forced_split=True,
            )
            result.append(child)
            cursor = chosen
        warnings.append(
            ChunkingWarning(
                code="forced_split",
                message="A block was split to satisfy hard chunk limits.",
                normalized_start=block.start,
                normalized_end=block.end,
            )
        )
        return result

    def _maximum_end(self, value: str, start: int) -> int:
        character_end = min(len(value), start + self.config.maximum_characters)
        spans = self.tokenizer.spans(value[start:character_end])
        if len(spans) <= self.config.maximum_token_count:
            return character_end
        return start + spans[self.config.maximum_token_count - 1].end

    @staticmethod
    def _safe_split_boundaries(value: str) -> list[int]:
        return [match.end() for match in _SENTENCE_END.finditer(value)]

    def _within_limit(self, value: str) -> bool:
        return (
            len(value) <= self.config.maximum_characters
            and self.tokenizer.count(value) <= self.config.maximum_token_count
        )

    def _pack(self, text: str, blocks: list[_Block]) -> list[_ChunkSpan]:
        spans: list[_ChunkSpan] = []
        current: list[_Block] = []
        for block in blocks:
            if not current:
                current = [block]
                continue
            proposed = text[current[0].start : block.end]
            boundary = self._hard_boundary(current[-1], block)
            heading_start = AnnotationType.HEADING_REGION.value in block.block_types
            target_reached = (
                self.tokenizer.count(text[current[0].start : current[-1].end])
                >= self.config.target_token_count
            )
            if boundary or not self._within_limit(proposed) or target_reached or heading_start:
                spans.append(_ChunkSpan(current[0].start, current[-1].end, list(current)))
                current = [block]
            else:
                current.append(block)
        if current:
            spans.append(_ChunkSpan(current[0].start, current[-1].end, list(current)))
        return spans

    def _hard_boundary(self, left: _Block, right: _Block) -> bool:
        if (
            self.config.preserve_page_boundaries
            and left.pages
            and right.pages
            and left.pages != right.pages
        ):
            return True
        if left.sections and right.sections and left.sections != right.sections:
            return True
        if (
            left.heading_path
            and right.heading_path
            and left.heading_path[0] != right.heading_path[0]
        ):
            return True
        if self.config.preserve_tables and (
            AnnotationType.TABLE_REGION.value in left.block_types
        ) != (AnnotationType.TABLE_REGION.value in right.block_types):
            return True
        if self.config.preserve_code_blocks and (
            AnnotationType.CODE_REGION.value in left.block_types
        ) != (AnnotationType.CODE_REGION.value in right.block_types):
            return True
        if (
            not self.config.merge_small_adjacent_sections
            and left.heading_path != right.heading_path
        ):
            return True
        return False

    def _apply_overlap(
        self, text: str, spans: list[_ChunkSpan], warnings: list[ChunkingWarning]
    ) -> list[_ChunkSpan]:
        requested = self.config.overlap_token_count
        if requested == 0:
            return spans
        for index in range(1, len(spans)):
            previous, current = spans[index - 1], spans[index]
            if self._unrelated(previous, current):
                continue
            previous_types = {kind for block in previous.blocks for kind in block.block_types}
            if (
                AnnotationType.TABLE_REGION.value in previous_types
                or AnnotationType.CODE_REGION.value in previous_types
            ):
                warnings.append(
                    ChunkingWarning(
                        code="overlap_reduced",
                        message="Overlap was skipped across a protected structural block.",
                        normalized_start=current.start,
                        normalized_end=current.end,
                    )
                )
                continue
            tokens = self.tokenizer.spans(text[previous.start : previous.end])
            current_tokens = self.tokenizer.count(text[current.start : current.end])
            ratio = self.config.maximum_overlap_ratio
            ratio_limit = int(current_tokens * ratio / (1 - ratio)) if ratio < 1 else current_tokens
            overlap = min(requested, max(0, len(tokens) - 1), ratio_limit)
            if overlap == 0:
                continue
            overlap_start = previous.start + tokens[-overlap].start
            if (
                self.tokenizer.count(text[overlap_start : current.end])
                > self.config.maximum_token_count
            ):
                allowed = max(
                    0,
                    self.config.maximum_token_count
                    - self.tokenizer.count(text[current.start : current.end]),
                )
                overlap = min(overlap, allowed)
                if overlap == 0:
                    warnings.append(
                        ChunkingWarning(
                            code="overlap_reduced",
                            message="Overlap was omitted to preserve the maximum chunk size.",
                            normalized_start=current.start,
                            normalized_end=current.end,
                        )
                    )
                    continue
                overlap_start = previous.start + tokens[-overlap].start
            current.overlap_start = current.start
            current.start = overlap_start
        return spans

    @staticmethod
    def _unrelated(previous: _ChunkSpan, current: _ChunkSpan) -> bool:
        left, right = previous.blocks[-1], current.blocks[0]
        if left.pages and right.pages and left.pages != right.pages:
            return True
        if left.sections and right.sections and left.sections != right.sections:
            return True
        if (
            left.heading_path
            and right.heading_path
            and left.heading_path[0] != right.heading_path[0]
        ):
            return True
        return False

    def _chunk_model(
        self,
        document: Document,
        normalized: NormalizationResult,
        span: _ChunkSpan,
        index: int,
        warnings: list[ChunkingWarning],
    ) -> Chunk:
        segments = [
            segment
            for segment in normalized.segments
            if self._intersects(
                span.start, span.end, segment.normalized_start, segment.normalized_end
            )
        ]
        approximate = not segments or any(segment.approximate for segment in segments)
        if segments:
            original_start = min(segment.original_start for segment in segments)
            original_end = max(segment.original_end for segment in segments)
            source = self._aggregate_source(document.source, segments)
        else:
            original_start = original_end = 0
            source = document.source
        if approximate:
            warnings.append(
                ChunkingWarning(
                    code="approximate_mapping",
                    message="A chunk maps approximately to original parsed content.",
                    normalized_start=span.start,
                    normalized_end=span.end,
                )
            )
        normalized_content = normalized.normalized_content[span.start : span.end]
        original_content = document.content[original_start:original_end]
        block_types = sorted({kind for block in span.blocks for kind in block.block_types})
        pages = sorted({page for block in span.blocks for page in block.pages})
        sections = sorted({section for block in span.blocks for section in block.sections})
        parser_blocks = sorted({value for block in span.blocks for value in block.parser_blocks})
        headings = span.blocks[-1].heading_path if self.config.attach_heading_context else []
        config_identity = self._config_identity()
        chunk_id = self._stable_id(
            document.id,
            normalized.normalized_hash,
            config_identity,
            index,
            span.start,
            span.end,
            normalized_content,
        )
        metadata: dict[str, Any] = {
            "chunking_strategy": self.config.strategy.value,
            "chunker_version": self.version,
            "tokenizer": self.tokenizer.name,
            "tokenizer_version": self.tokenizer.version,
            "config_identity": config_identity,
            "normalized_start": span.start,
            "normalized_end": span.end,
            "original_start": original_start,
            "original_end": original_end,
            "forced_split": any(block.forced_split for block in span.blocks),
            "overlap_applied": span.overlap_start is not None,
            "overlap_original_chunk_start": span.overlap_start,
            "page_range": [pages[0], pages[-1]] if pages else [],
            "section_range": [sections[0], sections[-1]] if sections else [],
            "parser_blocks": parser_blocks,
            "block_types": block_types,
            "table_present": AnnotationType.TABLE_REGION.value in block_types,
            "code_block_present": AnnotationType.CODE_REGION.value in block_types,
            "list_present": AnnotationType.LIST_REGION.value in block_types,
            "approximate_source_mapping": approximate,
        }
        if (
            len(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
            > self.config.maximum_metadata_characters
        ):
            raise ChunkingError(
                ChunkingErrorCategory.INVALID_INPUT,
                "chunk metadata exceeds configured size limit",
            )
        return Chunk(
            id=chunk_id,
            document_id=document.id,
            index=index,
            content=original_content,
            normalized_content=normalized_content,
            content_hash=document_content_hash(normalized_content),
            token_count=self.tokenizer.count(normalized_content),
            character_count=len(original_content),
            source=source,
            headings=headings,
            metadata=metadata,
        )

    @staticmethod
    def _aggregate_source(source: SourceLocation, segments: list[Any]) -> SourceLocation:
        pages = sorted(
            {
                segment.source_location.page_number
                for segment in segments
                if segment.source_location.page_number is not None
            }
        )
        line_starts = [
            segment.source_location.line_start
            for segment in segments
            if segment.source_location.line_start is not None
        ]
        line_ends = [
            segment.source_location.line_end
            for segment in segments
            if segment.source_location.line_end is not None
        ]
        values = source.model_dump()
        values["page_number"] = pages[0] if pages else source.page_number
        values["line_start"] = min(line_starts) if line_starts else source.line_start
        values["line_end"] = max(line_ends) if line_ends else source.line_end
        return SourceLocation.model_validate(values)

    def _result(
        self,
        document: Document,
        normalized: NormalizationResult,
        chunks: list[Chunk],
        warnings: list[ChunkingWarning],
        blocks: int,
        forced_splits: int,
        overlap_tokens: int,
        approximate: int = 0,
    ) -> ChunkingResult:
        return ChunkingResult(
            document_id=document.id,
            normalized_hash=normalized.normalized_hash,
            chunks=chunks,
            warnings=warnings,
            statistics=ChunkingStatistics(
                input_characters=len(normalized.normalized_content),
                input_tokens=self.tokenizer.count(normalized.normalized_content),
                blocks=blocks,
                chunks=len(chunks),
                forced_splits=forced_splits,
                overlap_tokens=overlap_tokens,
                approximate_mappings=approximate,
            ),
            chunker_name=self.name,
            chunker_version=self.version,
            tokenizer_name=self.tokenizer.name,
            tokenizer_version=self.tokenizer.version,
            metadata={
                "config": self.config.model_dump(mode="json"),
                "config_identity": self._config_identity(),
                "content_removed": False,
                "summarized": False,
            },
        )

    def _config_identity(self) -> str:
        payload = json.dumps(
            self.config.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(
            f"chunk-config:v1:{self.version}:{self.tokenizer.name}:{self.tokenizer.version}:{payload}".encode()
        ).hexdigest()

    @staticmethod
    def _stable_id(*values: Any) -> str:
        payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"), default=str)
        return hashlib.sha256(f"chunk:v2:{payload}".encode()).hexdigest()

    @staticmethod
    def _intersects(start: int, end: int, other_start: int, other_end: int) -> bool:
        if start == end or other_start == other_end:
            return start <= other_start <= end
        return start < other_end and other_start < end
