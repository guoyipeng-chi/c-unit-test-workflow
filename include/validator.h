#ifndef VALIDATOR_H
#define VALIDATOR_H

#include <stdint.h>
#include "database.h"

#ifdef __cplusplus
extern "C" {
#endif

// Validation functions
int32_t validate_student_name(const char* name);
int32_t validate_score(float score);
int32_t validate_student_id(int32_t id);

#ifdef __cplusplus
}
#endif

#endif
