FROM public.ecr.aws/lambda/python:3.12
COPY --from=ghcr.io/astral-sh/uv:0.11.0 /uv /usr/local/bin/uv

WORKDIR ${LAMBDA_TASK_ROOT}

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt \
 && pip install --no-cache-dir -r /tmp/requirements.txt \
 && pip install --no-cache-dir --no-deps .

CMD ["garmin_tracker.lambda_handler.handler"]
