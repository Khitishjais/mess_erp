# Hugging Face "Docker" Space: builds in the cloud, nothing to install on your PC.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN useradd -m -u 1000 user && mkdir -p /home/user/app && chown -R user:user /home/user
WORKDIR /home/user/app
COPY --chown=user requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt
COPY --chown=user . .
USER user
# static files for the Django admin (build-time only; real secrets are injected when the Space runs)
RUN DEBUG=True python manage.py collectstatic --noinput
EXPOSE 7860
CMD ["bash", "start.sh"]
