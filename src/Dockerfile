FROM python:3.12.9-slim
#FROM public.ecr.aws/docker/library/python:3.12.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /code

# Install Python dependencies
COPY requirements.txt /code/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . /code/

# Expose port 3000 for the SSE server
EXPOSE 3000

# Start the app with uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]

# Create a non-root user
RUN useradd -m appuser
USER appuser