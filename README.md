# Campus Agent – University Appointment & Student Concern Management System

**Campus Agent** is a web-based university service management platform designed to simplify appointment scheduling, improve coordination between students and university staff, and provide a structured process for managing student concerns.

The platform brings essential campus services together through a centralised system with separate access for students, staff and the Chairperson.

**Project Status:** In Progress

---

## 1. Project Overview

University students often need to contact different departments and staff members for academic and administrative assistance. Managing these interactions through separate communication channels can make appointment coordination and concern tracking difficult.

Campus Agent aims to address this by providing a centralised digital platform where students can book appointments, manage their bookings and submit concerns, while staff and the Chairperson can manage their respective responsibilities.

## 2. Key Features

### Student Module
- Student registration and secure login using SRN.
- View staff details and available appointment slots.
- Book appointments with university staff.
- Cancel or reschedule existing appointments.
- View appointment information.
- Submit student concerns through the platform.

### Staff Module
- Staff login and dashboard access.
- View scheduled appointments.
- Access student details.
- Cancel or reschedule appointments.
- Manage student appointment requests.

### Chairperson Module
- Access submitted student concerns.
- View and manage student issues.
- Update concern status and track resolution.

### Additional Features
- Role-based access for students, staff and the Chairperson.
- Real-time appointment slot availability.
- In-app appointment notifications.
- Centralised PostgreSQL database.
- Automatic logout after inactivity.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend development |
| Streamlit | Web application interface |
| PostgreSQL | Database management |
| GitHub | Source code management and version control |

## 4. System Architecture

Campus Agent follows a simple application architecture:

1. **Frontend:** Streamlit provides the user interface and dashboards.
2. **Application Logic:** Python handles authentication, appointment workflows and user-specific operations.
3. **Database:** PostgreSQL stores student, staff, appointment and concern-related information.

## 5. Application Workflow

```text
             CAMPUS AGENT
                   |
          User Authentication
                   |
       -------------------------
       |           |           |
    Student      Staff     Chairperson
       |           |           |
   Book          View        View Student
 Appointment  Appointments     Concerns
       |           |           |
   Manage       Manage       Update Concern
  Bookings     Bookings        Status
       |           |           |
       -------------------------
                   |
             PostgreSQL
                Database
```

## 6. Project Objectives

- Digitise university appointment scheduling and management.
- Provide students with a single platform to access campus services.
- Improve coordination between students and university staff.
- Establish a structured process for submitting and managing student concerns.
- Explore the use of digital systems in improving administrative workflows.

## 7. Current Development Status

Campus Agent has been developed with separate student, staff and Chairperson modules. Its major appointment and student concern management workflows have undergone functional testing using multiple test accounts.

Further development and testing are ongoing, with scope for improvements in system usability, staff availability management and broader real-world evaluation.

## 8. Future Enhancements

- Staff self-service availability and scheduling management.
- Expanded department integration.
- Advanced appointment analytics and reporting.
- Improved dashboard visualisation.
- Real-world testing and user feedback.
- Additional administrative features based on institutional requirements.

## 9. Project Information

**Project Name:** Campus Agent  
**Category:** Web Application | University Management System  
**Domain:** Business Analytics | Digital Transformation | Information Systems  
**Development Status:** In Progress

---

*Campus Agent aims to make university services more accessible, organised and manageable through a centralised digital platform.*
