#include <string.h>
#include "database.h"

#define MAX_STUDENTS 100
static Student students[MAX_STUDENTS];
static int32_t student_count = 0;

int32_t db_init(void) {
    student_count = 0;
    memset(students, 0, sizeof(students));
    return 0;
}

int32_t db_add_student(const Student* student) {
    if (student_count >= MAX_STUDENTS) {
        return -1;
    }
    if (student == NULL) {
        return -1;
    }
    
    students[student_count] = *student;
    student_count++;
    return 0;
}

int32_t db_get_student(int32_t id, Student* student) {
    if (student == NULL) {
        return -1;
    }
    
    for (int32_t i = 0; i < student_count; i++) {
        if (students[i].id == id) {
            *student = students[i];
            return 0;
        }
    }
    return -1;
}

int32_t db_update_score(int32_t id, float score) {
    for (int32_t i = 0; i < student_count; i++) {
        if (students[i].id == id) {
            students[i].score = score;
            return 0;
        }
    }
    return -1;
}

int32_t db_delete_student(int32_t id) {
    for (int32_t i = 0; i < student_count; i++) {
        if (students[i].id == id) {
            memmove(&students[i], &students[i + 1], 
                    (student_count - i - 1) * sizeof(Student));
            student_count--;
            return 0;
        }
    }
    return -1;
}
