---
layout: default
title: Magic Studio and dialogue examples
permalink: /examples/ssml.html
sidebar: false
wide: true
content_class: ssml-content ssml-page
stylesheets:
  - /examples/ssml.css
  - /examples/website.css
scripts:
  - /examples/ssml.js
---
{% capture showcase %}{% include_relative ssml.html %}{% endcapture %}
<div class="page-shell">
{{ showcase | split: '<main class="page-shell">' | last | split: '</main>' | first | strip }}
</div>
<div class="toast" role="status" aria-live="polite" hidden></div>
