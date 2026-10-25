# Linux like the GitHub Actions runner (Ubuntu, x86_64, uv's Python 3.14),
# to reproduce CI failures locally, e.g. on a Mac with Docker or colima:
#
#   docker build --platform linux/amd64 -t woodwright-ci .
#   docker run --rm --platform linux/amd64 woodwright-ci                 # the tests
#   docker run --rm --platform linux/amd64 woodwright-ci \
#     uv run woodwright export --all --out /tmp/out                     # the docs' exports
#
# To try changes without rebuilding, mount the source over the image's (the
# project is installed editable): `-v "$PWD/src:/app/src" -v "$PWD/tests:/app/tests"`.
FROM ubuntu:24.04

# What the runner has and the slim image lacks: OpenGL for OpenCascade, and
# the fonts the plans use for non-Latin-1 text.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgl1 libglu1-mesa fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
ENV UV_PYTHON=3.14 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv python install 3.14

WORKDIR /app
# The dependencies first, so that changing the code doesn't reinstall them.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --group docs --no-install-project
COPY . .
RUN uv sync --locked --group docs

CMD ["uv", "run", "pytest"]
