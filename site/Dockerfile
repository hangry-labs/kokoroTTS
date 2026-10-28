FROM ruby:3.4-slim@sha256:09125b2be429d65151802d2a04a60e0817fb8f380195fedbc3e3d8b51b12c049
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git libffi-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /builder
COPY Gemfile Gemfile.lock ./
RUN bundle config set deployment true && bundle install --jobs 4 --retry 3
ENV JEKYLL_ENV=production BUNDLE_GEMFILE=/builder/Gemfile
ENTRYPOINT ["bundle", "exec", "jekyll"]
