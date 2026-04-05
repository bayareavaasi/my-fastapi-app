# 1. Start with a lightweight Python image
FROM python:3.12-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy only the requirements first (for better caching)
COPY requirements.txt .

# 4. Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the source code into the container
COPY ./src ./src

# 6. Expose the port FastAPI runs on
EXPOSE 8000

# 7. The command to run the app in production mode
CMD ["fastapi", "run", "src/app/main.py", "--port", "8000"]
