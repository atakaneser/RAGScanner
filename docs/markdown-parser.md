# Markdown parser

Markdown parser `.md`/`.markdown` içeriğini orijinal Markdown metni olarak korur. HTML render
etmez, embedded code çalıştırmaz, link/image fetch etmez ve remote kaynak çözmez.

Title sırası: bounded `---` scalar front matter `title`, ilk fenced-code dışı H1, filename stem.
Front matter ilk 100 satır/16 KiB içinde kapanmalı; yalnız basit `key: scalar` alınır. Nested YAML,
tag, anchor veya object construction yoktur. Secret-like değerler redakte edilir. Heading metadata
level/text/line taşır; code fence içi yok sayılır. Markdown/HTML daima untrusted text'tir.
