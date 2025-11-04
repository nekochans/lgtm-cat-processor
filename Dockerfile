FROM public.ecr.aws/lambda/python:3.12

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv export --frozen --no-dev --no-emit-project -o requirements.txt


COPY src ${LAMBDA_TASK_ROOT}
COPY fonts ${LAMBDA_TASK_ROOT}/fonts

RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
CMD ["main.lambda_handler"]
