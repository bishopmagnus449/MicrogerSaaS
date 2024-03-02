# Use node:20 as the first stage
FROM node:20 as node

# Set the working directory to /app
WORKDIR /app

# Copy the project files into the image
COPY frontend/MicrogerSaaS .

# Install and build the frontend dependencies
RUN npm install && npm run build

# Use python:3.10 as the second stage
FROM python:3.10 as python

# Set the working directory to /app/backend
WORKDIR /app

COPY backend .

# Copy the frontend build output from the node stage
COPY --from=node /app/dist /app/MicrogerSaaS/static

# Install the backend dependencies
RUN pip3 install -r requirements.txt

# Run the Django migrations and collect the static files
RUN python3 manage.py makemigrations MicrogerSaaS && python3 manage.py migrate && python3 manage.py collectstatic --clear

# Copy the index.html file to the templates directory
RUN cp staticfiles/index.html templates/

# Expose port 8000
EXPOSE 8000

# Run the Django app
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
