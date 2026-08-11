---
layout: page
permalink: /publications/
title: Publications
description: Reversed chronological order.
nav: true
nav_order: 2
---

<!-- _pages/publications.md -->

<!-- Bibsearch Feature -->

{% include bib_search.liquid %}

<div class="publications">

{% bibliography %}

</div>

<script defer src="{{ '/assets/js/bibtex-copy.js' | relative_url | bust_file_cache }}"></script>
