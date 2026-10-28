---
layout: default
title: Voice examples
permalink: /examples/
sidebar: false
wide: true
content_class: gallery-content page-shell
stylesheets:
  - /examples/gallery.css
  - /examples/website.css
scripts:
  - /examples/voices.js
  - /examples/player.js
  - /examples/website.js
---
{% capture gallery %}{% include_relative index.html %}{% endcapture %}
{{ gallery | split: '<main class="page-shell">' | last | split: '</main>' | first | strip }}
