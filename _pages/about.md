---
layout: about
title: About
permalink: /
subtitle: >
  <span class="affil"><strong>Ph.D. candidate</strong> — School of Computer Science, China University of Geosciences (Wuhan, China)</span><br>
  <span class="affil"><strong>Visiting Ph.D. student</strong> — College of Computing and Data Science, Nanyang Technological University (Singapore)</span>

profile:
  align: right
  image: prof_pic.jpg
  image_circular: false # crops the image to make it circular

selected_papers: false # includes a list of papers marked as "selected={true}"
social: true # includes social icons at the bottom of the page

announcements:
  enabled: true # includes a list of news items
  scrollable: true # adds a vertical scroll bar if there are more than 3 news items
  limit: 5 # leave blank to include all the news in the `_news` folder

latest_posts:
  enabled: false
---

**Yanchi Li (李延炽)** is a Ph.D. candidate at CUG since 2023, supervised by Prof. Wenyin Gong, and co-supervised by Prof. Qiong Gu (HBUAS) and Prof. Yew-Soon Ong (NTU).

{% assign total_citations = 0 %}
{% for paper in site.data.citations.papers %}
  {% assign total_citations = total_citations | plus: paper[1].citations %}
{% endfor %}
<div class="citation-box">
  <span class="citation-box-label">Total Citations</span>
  <span class="citation-box-count">{{ total_citations }}</span>
</div>
<div class="citation-box">
  <span class="citation-box-label">GitHub Stars</span>
  <span class="citation-box-count">{{ site.data.github.total_stars }}</span>
</div>

**Email:** int_lyc@cug.edu.cn

## Research Interests

<div class="service-blocks">
  <span class="service-block">Evolutionary Multitasking</span>
  <span class="service-block">Multitask Optimization</span>
  <span class="service-block">Evolutionary Reinforcement Learning</span>
</div>

## Reviewing & Services

<div class="service-group">
  <div class="service-group-title">Journals</div>
  <div class="service-blocks">
    <span class="service-block">IEEE TEVC</span>
    <span class="service-block">IEEE TSMC-S</span>
    <span class="service-block">IEEE CIM</span>
    <span class="service-block">AI Review</span>
    <span class="service-block">Swarm Evol. Comput.</span>
    <span class="service-block">Expert Syst. Appl.</span>
  </div>
</div>

<div class="service-group">
  <div class="service-group-title">Conferences</div>
  <div class="service-blocks">
    <span class="service-block">ICML</span>
    <span class="service-block">AAAI</span>
    <span class="service-block">ACM MM</span>
  </div>
</div>
