# Group Project Proposal

## Library Management System

**Module Tutor:** Dr James Xue  
**Submission Deadline:** End of Week 3

## Group Members

| Full Name | Student ID | Primary Role |
| --- | --- | --- |
| Sujata Mainali | 24832107 | Documentation and Testing |
| Shiva Shrestha | 24826325 | Planning and Frontend Support |
| Jigyasa Khadka | 24820276 | Backend Development |
| Muhammad Haseeb | 24828895 | Backend and System Support |
| Nirajan Mandal | 24820191 | Database and Testing |
| Prashish Khanal | 24826785 | Book Management Features |
| Shiv Shankar Sah | 24829173 | Presentation and Project Coordination |

## 1. Introduction and Problem Statement

Libraries are an essential part of academic institutions because they provide students and staff with access to books, journals, and learning materials. However, many small and medium-sized libraries still rely on manual record keeping or basic spreadsheet systems to manage books, users, and borrowing activities. These traditional methods are often slow, inefficient, and prone to human error.

In a manual system, staff must update records each time a book is borrowed, returned, added, or removed. This process increases the likelihood of mistakes such as incorrect stock counts, missing records, or difficulty tracking overdue books. It also makes it harder for library staff to provide fast and accurate service to users.

From the user perspective, the absence of a digital system creates inconvenience. Students and staff may need to visit the library in person just to check whether a book is available. This wastes time and reduces the overall efficiency of the library service.

To solve these problems, this project proposes the development of a web-based Library Management System. The system will allow administrators to manage books digitally and enable users to register, log in, and access the catalogue through an easy-to-use interface. The project will improve efficiency, reduce errors, and provide a more modern and accessible library service.

## 2. Purpose, Aim and Objectives

### 2.1 Purpose

The purpose of this project is to replace manual and semi-manual library processes with a centralised digital system that allows library activities to be managed more efficiently. The system will improve how books, users, and transactions are handled and will provide a better experience for both library staff and members.

### 2.2 Aim

The aim of this project is to design, develop, and test a functional web-based Library Management System using Python Flask, MySQL, HTML, and CSS, supported by Docker for database setup, so that library staff can manage books digitally and users can register and log in to access the system.

### 2.3 SMART Objectives

1. Design and implement a user registration and login module that allows users to create accounts and securely access the system by Week 6.
2. Develop a book catalogue module that supports create and view operations, with update and delete functionality added during later development, by Week 8.
3. Build a MySQL database to store user and book information accurately and reliably by Week 6.
4. Create a responsive and user-friendly interface for registration, login, dashboard, and book management pages by Week 8.
5. Integrate the Flask application with a MySQL database running through Docker and test all core features before the final demonstration by Week 11.
6. Carry out system testing, fix identified errors, and document results in the group report by Week 11.

## 3. Main Features of the Proposed System

The proposed Library Management System will include the following core features:

### 3.1 User Registration and Login

Users will be able to register an account and log in to the system using their email address and password. This provides controlled access to the application and ensures that only authorised users can use the system.

### 3.2 Dashboard

After logging in, users will be directed to a dashboard that acts as the main navigation page. From here, they can access the book management features and other system pages.

### 3.3 Book Management

The system will allow administrators or authorised users to add books into the database and view existing books in a structured format. As the project progresses, update and delete features will also be added to support full CRUD operations.

### 3.4 Database Integration

The system will use MySQL as the relational database. It will store user records and book records, allowing persistent and structured data management.

### 3.5 Responsive User Interface

The frontend will be built using HTML and CSS, with an emphasis on simple navigation, readable forms, and a clear layout suitable for demonstration and practical use.

## 4. Methodology

### 4.1 Requirements Gathering

During the early phase of the project, the group discussed the common problems found in traditional library management systems, such as manual record keeping, difficulty tracking borrowed books, and the lack of a quick search process. These discussions helped define the functional and non-functional requirements of the system.

The main functional requirements identified were:

- user registration and login
- book catalogue management
- viewing books stored in the system
- CRUD functionality for book records

The non-functional requirements included:

- usability
- basic security
- responsiveness
- reliability

### 4.2 System Design

The design phase includes planning the application structure, database, and user interface. The project follows a simple web application structure in which:

- Flask handles routing and backend logic
- MySQL stores system data
- HTML templates render the frontend pages
- CSS is used to improve layout and presentation

The database design focuses on at least two main entities:

- `users`
- `books`

Additional entities such as borrowing records may be added later if the project is extended.

### 4.3 System Build Approach

The project is being implemented using the following technology stack:

- **Backend:** Python Flask
- **Frontend:** HTML and CSS
- **Database:** MySQL
- **Development Tools:** Visual Studio Code, GitHub
- **Container Support:** Docker for running MySQL locally

The decision to use Flask instead of a JavaScript-based backend was based on the group’s practical development progress, familiarity with Python, and the need to produce a working prototype within the project timeline.

### 4.4 Testing and Evaluation

Testing will be carried out throughout development to ensure the system works correctly. This includes:

- checking user registration and login functionality
- testing database connectivity
- testing form validation
- testing book addition and book listing
- checking whether pages display correctly and are easy to use

Any bugs found during testing will be corrected and recorded in the final report.

## 5. Legal, Ethical and Privacy Considerations

### 5.1 Data Protection

The system stores user information such as names, email addresses, and passwords. This means the project must consider privacy and responsible data handling. Only data required for the operation of the system should be collected.

### 5.2 Security

Basic security measures must be applied. For example, access to internal pages should require login, and future improvements should include password hashing and stronger session protection.

### 5.3 Ethical Considerations

The project is intended for academic purposes only. All work submitted should reflect the real development process carried out by the group. Any tools, frameworks, and resources used should be properly acknowledged where required.

### 5.4 Accessibility

The interface should be designed to be easy to read and use. This includes clear labels, readable colours, and simple navigation. The project should consider accessibility principles where possible.

## 6. Resources Required

The project requires the following resources:

| Category | Resource | Estimated Cost | Availability |
| --- | --- | --- | --- |
| Hardware | Personal laptops | No additional cost | Confirmed |
| Software | Visual Studio Code | Free | Available |
| Software | Python | Free | Available |
| Software | Flask | Free | Available |
| Software | MySQL | Free | Available |
| Software | Docker Desktop | Free | Available |
| Software | Git and GitHub | Free | Available |
| Documentation | Microsoft Word | University licence | Available |
| Communication | WhatsApp / Teams | Free | Available |

All required tools are freely available or provided through the university, so no major cost is expected.

## 7. Project Plan

The project follows a twelve-week development plan:

| Task / Activity | W1 | W2 | W3 | W4 | W5 | W6 | W7 | W8 | W9 | W10 | W11 | W12 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Requirements gathering and topic selection | ■ | ■ |  |  |  |  |  |  |  |  |  |  |
| System and database design |  | ■ | ■ |  |  |  |  |  |  |  |  |  |
| User registration and login |  |  | ■ | ■ | ■ |  |  |  |  |  |  |  |
| Book management development |  |  |  | ■ | ■ | ■ | ■ |  |  |  |  |  |
| Frontend improvement |  |  |  | ■ | ■ | ■ | ■ |  |  |  |  |  |
| Database integration and testing |  |  |  |  | ■ | ■ | ■ | ■ |  |  |  |  |
| Bug fixing and refinement |  |  |  |  |  |  |  | ■ | ■ | ■ |  |  |
| Report writing and documentation |  |  |  |  |  | ■ | ■ | ■ | ■ | ■ |  |  |
| Presentation preparation |  |  |  |  |  |  |  |  |  | ■ | ■ | ■ |

The group will continue reviewing progress weekly and adjusting tasks where needed to make sure the final system and report reflect the actual work completed.
