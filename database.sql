CREATE DATABASE IF NOT EXISTS library_db;
USE library_db;

DROP TABLE IF EXISTS borrow;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    author VARCHAR(100),
    category VARCHAR(100),
    cover_url VARCHAR(500) NULL,
    quantity INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE borrow (
    borrow_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    book_id INT,
    borrow_date DATE,
    return_date DATE NULL,
    due_date DATE NULL,
    returned_at DATE NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

INSERT INTO users (user_id, name, email, password, role) VALUES
(1, 'Jigyasa khadka', 'jigyasa.khadka24@my.northampton.ac.uk', '123', 'admin'),
(2, 'Cresthava', 'cresthava123@gmail.com', 'group9', 'admin'),
(3, 'Shiva Shrestha', 'shivashrestha14@gmail.com', '123', 'admin'),
(4, 'Shiva', 'shiva@gmail.com', '123', 'admin'),
(5, 'Sujata Mainali', 'sujatamainali@gmail.com', '123', 'admin'),
(6, 'Nirajan Mandal', 'nirajanmandal@gmail.com', '123', 'admin'),
(7, 'Prashish', 'prashish@gmail.com', '123', 'admin'),
(8, 'Muhammad Haseeb', 'muhammadhaseeb@gmail.com', '123', 'admin'),
(9, 'James Xue', 'jamesxue@gmail.com', '123', 'admin');

INSERT INTO books (book_id, title, author, category, cover_url, quantity) VALUES
(7, 'Database System Concepts', 'Abraham Silberschatz', 'Database', 'https://covers.openlibrary.org/b/isbn/9780073523323-L.jpg', 3),
(8, 'Computer Networks', 'Andrew S. Tanenbaum', 'Networking', 'https://covers.openlibrary.org/b/isbn/9780132126953-L.jpg', 4),
(9, 'Artificial Intelligence: A Modern Approach', 'Stuart Russell', 'Artificial Intelligence', 'https://covers.openlibrary.org/b/isbn/9780134610993-L.jpg', 2),
(10, 'Python Crash Course', 'Eric Matthes', 'Programming', 'https://covers.openlibrary.org/b/isbn/9781593279288-L.jpg', 6),
(11, 'Operating System Concepts', 'Abraham Silberschatz', 'Operating Systems', 'https://covers.openlibrary.org/b/isbn/9781118063330-L.jpg', 3),
(12, 'The Pragmatic Programmer', 'Andrew Hunt', 'Programming', 'https://covers.openlibrary.org/b/isbn/9780201616224-L.jpg', 4),
(13, 'To Kill a Mockingbird', 'Harper Lee', 'Fiction', 'https://covers.openlibrary.org/b/isbn/9780061120084-L.jpg', 5),
(14, '1984', 'George Orwell', 'Dystopian', 'https://covers.openlibrary.org/b/isbn/9780451524935-L.jpg', 4),
(15, 'Pride and Prejudice', 'Jane Austen', 'Romance', 'https://covers.openlibrary.org/b/isbn/9780141439518-L.jpg', 3),
(16, 'The Hobbit', 'J.R.R. Tolkien', 'Fantasy', 'https://covers.openlibrary.org/b/isbn/9780261103344-L.jpg', 5),
(17, 'The Diary of a Young Girl', 'Anne Frank', 'Biography', 'https://covers.openlibrary.org/b/isbn/9780553296983-L.jpg', 2),
(18, 'Clean Code', 'Robert C. Martin', 'Software Engineering', 'https://covers.openlibrary.org/b/isbn/9780132350884-L.jpg', 4),
(19, 'Introduction to Algorithms', 'Thomas H. Cormen', 'Computer Science', 'https://covers.openlibrary.org/b/isbn/9780262046305-L.jpg', 5);

INSERT INTO borrow (borrow_id, user_id, book_id, borrow_date, return_date, due_date, returned_at) VALUES
(1, 1, 7, CURDATE() - INTERVAL 10 DAY, NULL, CURDATE() + INTERVAL 4 DAY, NULL),
(2, 1, 8, CURDATE() - INTERVAL 16 DAY, NULL, CURDATE() - INTERVAL 2 DAY, NULL),
(3, 1, 9, CURDATE() - INTERVAL 20 DAY, NULL, CURDATE() - INTERVAL 6 DAY, CURDATE() - INTERVAL 1 DAY),
(4, 1, 10, CURDATE() - INTERVAL 5 DAY, NULL, CURDATE() + INTERVAL 9 DAY, NULL),
(5, 1, 11, CURDATE() - INTERVAL 30 DAY, NULL, CURDATE() - INTERVAL 15 DAY, CURDATE() - INTERVAL 10 DAY);
