#include <string.h>
#include "student_manager.h"
#include "validator.h"

static int32_t g_next_id = 1;

int32_t add_student(const char* name, float initial_score) {
    if (validate_student_name(name) != 0) {
        return -1;
    }
    if (validate_score(initial_score) != 0) {
        return -1;
    }
    
    Student student;
    student.id = g_next_id++;
    strncpy(student.name, name, 63);
    student.name[63] = '\0';
    student.score = initial_score;
    
    if (db_add_student(&student) != 0) {
        return -1;
    }
    
    return student.id;
}

int32_t update_student_score(int32_t id, float new_score) {
    if (validate_student_id(id) != 0) {
        return -1;
    }
    if (validate_score(new_score) != 0) {
        return -1;
    }
    
    if (db_update_score(id, new_score) != 0) {
        return -1;
    }
    
    return 0;
}

float get_average_score(void) {
    int32_t count = get_total_students();
    if (count == 0) {
        return 0.0f;
    }
    
    float total = 0.0f;
    for (int32_t i = 0; i < count; i++) {
        Student student;
        if (db_get_student(i + 1, &student) == 0) {
            total += student.score;
        }
    }
    
    return total / count;
}

int32_t get_total_students(void) {
    // This is a stub that would normally query database
    return g_next_id - 1;
}
