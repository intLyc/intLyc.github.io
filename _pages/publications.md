---
layout: page
permalink: /publications/
title: Publications
description: Selected publications for which I am the first or corresponding author.
_styles: |
  .post-description,
  .publications-list-note {
    font-size: 0.875rem;
    line-height: 1.5;
  }

  .post-description {
    margin-bottom: 0.15rem;
  }

  .publications-list-note {
    margin-top: 0;
    margin-bottom: 2rem;
  }
nav: true
nav_order: 2
---

<!-- _pages/publications.md -->

<p class="publications-list-note">For the complete publication list, please visit my <a href="https://scholar.google.com/citations?user=h7hvzUEAAAAJ" target="_blank" rel="external nofollow noopener">Google Scholar profile</a>.</p>

<!-- Bibsearch Feature -->

{% include bib_search.liquid %}

<div class="publications">

{% bibliography %}

</div>

<script defer src="{{ '/assets/js/bibtex-copy.js' | relative_url | bust_file_cache }}"></script>
