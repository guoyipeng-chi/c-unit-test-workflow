#ifndef STUDENT_MANAGER_H
#define STUDENT_MANAGER_H

#include <stdint.h>
#include "database.h"

#ifdef __cplusplus
extern "C" {
#endif

// Student management operations
int32_t add_student(const char* name, float initial_score);
int32_t update_student_score(int32_t id, float new_score);
float get_average_score(void);
int32_t get_total_students(void);

#ifdef __cplusplus
}
#endif

#endif
