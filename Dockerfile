FROM public.ecr.aws/lambda/python:3.12

WORKDIR /app

COPY src ${LAMBDA_TASK_ROOT}
COPY requirements.lock ./

RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r requirements.lock --target "${LAMBDA_TASK_ROOT}"

CMD ["main.lambda_handler"]
