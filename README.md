# Library Management System

This project is a web-based Library Management System built for our group assignment. It was developed using Python Flask, MySQL, HTML, CSS, Docker, and GitHub. The system allows users to register, log in, browse books, borrow and return books, and view dashboard information. It also includes admin features such as book management, registered user monitoring, notifications, and overdue fine tracking.

# Main Features

## User Features
- User registration and login
- View available books
- Search books by title, author, or category
- Borrow and return books
- View due dates
- View overdue fine information
- See notifications and reading history

## Admin Features
- Add books
- Edit books
- Delete books
- View registered users
- View dashboard statistics
- Monitor overdue books
- View notification alerts
- Track fine-related information

# Technologies Used
- Python
- Flask
- MySQL
- HTML
- CSS
- Docker
- GitHub

# Project Files
- `app.py` : Main Flask application
- `config.py` : Database connection settings
- `requirements.txt` : Required Python packages
- `database.sql` : Prepared database structure and sample data
- `templates/` : All HTML pages used in the project

# How To Run The Project

## 1. Install Python Packages

Open the terminal in the project folder and run:

```powershell
python -m pip install -r requirements.txt
```

## 2. Start Docker Desktop

Open Docker Desktop and wait until the engine is running.

## 3. Create MySQL Docker Container

Run:

```powershell
docker run --name library_mysql -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=library_system -p 3307:3306 -d mysql:8.0
```

If the container already exists, run:

```powershell
docker start library_mysql
```

## 4. Import Database

Run:

```powershell
Get-Content database.sql | docker exec -i library_mysql mysql -u root -proot library_system
```

## 5. Run Flask Application

Run:

```powershell
python app.py
```

## 6. Open The Website

Open a browser and visit:

```text
http://127.0.0.1:5000
```

# Demo Login Credentials

## Admin Login

Email: jigyasa.khadka24@my.northampton.ac.uk  
Password: 123

## Alternative Admin Login

Email: cresthava123@gmail.com  
Password: group9

# Team Members
- Jigyasa Khadka
- Sujata Mainali
- Shiva Shrestha
- Muhammad Haseeb
- Nirajan Mandal
- Prashish Khanal
- Shiv Shankar Sah

# Project Objective

The main objective of this project is to develop a secure and user-friendly digital Library Management System that improves book management, borrowing operations, notifications, and overdue tracking compared to traditional manual systems.

# Future Improvements
- Email notification system
- Online reservation system
- QR code integration
- Advanced analytics dashboard
- Mobile responsive optimization
- Online fine payment system

# GitHub Repository

https://github.com/Shiva24-bsc/library-management-system