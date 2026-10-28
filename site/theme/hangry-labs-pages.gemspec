# SPDX-License-Identifier: Apache-2.0
Gem::Specification.new do |spec|
  spec.name = "hangry-labs-pages"
  spec.version = "0.1.0"
  spec.authors = ["Hangry Labs"]
  spec.summary = "A README-first Hangry Labs theme for Jekyll project websites."
  spec.homepage = "https://hangrylabs.app/"
  spec.license = "Apache-2.0"
  spec.required_ruby_version = ">= 3.0"
  spec.files = Dir["_layouts/**/*", "assets/**/*", "LICENSE"]
  spec.add_runtime_dependency "jekyll", ">= 3.10", "< 5"
  spec.add_runtime_dependency "jekyll-seo-tag", "~> 2.8"
end
