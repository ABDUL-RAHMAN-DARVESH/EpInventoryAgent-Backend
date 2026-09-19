FROM python:3.12-slim

WORKDIR /app

# psycopg[binary] ships prebuilt wheels, so no compiler/apt packages needed
# beyond what the slim base already has.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .

RUN useradd --create-home appuser
USER appuser

# Most PaaS platforms (Railway, Render, Fly) inject PORT at runtime; default
# to 8000 for a plain `docker run` elsewhere.
ENV PORT=8000
EXPOSE 8000

# Applies any pending migrations, then starts the API. Fine as the single
# startup step while there's one instance; once there's more than one
# replica, move migrations to a separate release/pre-deploy step instead of
# running them from every container's boot to avoid a startup race.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
