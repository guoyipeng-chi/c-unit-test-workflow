#ifndef DATABASE_H
#define DATABASE_H

#include <stdint.h>

typedef struct {
    int32_t id;
    char name[64];
    float score;
} Student;

#ifdef __cplusplus
extern "C" {
#endif

// Database operations
int32_t db_init(void);
int32_t db_add_student(const Student* student);
int32_t db_get_student(int32_t id, Student* student);
int32_t db_update_score(int32_t id, float score);
int32_t db_delete_student(int32_t id);

#ifdef __cplusplus
}
#endif

#endif
