#include <string.h>
#include <ctype.h>
#include "validator.h"

int32_t validate_student_name(const char* name) {
    if (name == NULL || strlen(name) == 0) {
        return -1;
    }
    if (strlen(name) > 63) {
        return -1;
    }
    return 0;
}

int32_t validate_score(float score) {
    if (score < 0.0f || score > 100.0f) {
        return -1;
    }
    return 0;
}

int32_t validate_student_id(int32_t id) {
    if (id <= 0) {
        return -1;
    }
    return 0;
}
