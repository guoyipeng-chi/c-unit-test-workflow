#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "student_manager.h"
#include "database.h"
#include "validator.h"

using ::testing::Return;
using ::testing::_;

/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */

// student_manager.c 中的函数调用以下函数，需要Mock：
// 1. validate_student_name()  - 验证学生名字
// 2. validate_score()         - 验证分数
// 3. db_add_student()         - 添加学生到数据库
// 4. db_update_score()        - 更新学生分数
// 5. db_get_student()         - 获取学生信息
// 6. get_total_students()     - 获取学生总数

// 模板示例（实际使用时可取消注释并修改）：
// #define MOCK_VALIDATE_STUDENT_NAME_RETURN  0     // 验证通过
// #define MOCK_VALIDATE_SCORE_RETURN         0     // 分数有效
// #define MOCK_DB_ADD_STUDENT_RETURN         0     // 添加成功
// #define MOCK_DB_UPDATE_SCORE_RETURN        0     // 更新成功
// #define MOCK_DB_GET_STUDENT_RETURN         0     // 获取成功

/* ================================================= */

class StudentManagerTest : public ::testing::Test {
protected:
    void SetUp() override {
        db_init();
    }
    
    void TearDown() override {
        db_init();
    }
};

TEST_F(StudentManagerTest, TestCase1_AddStudent_Valid) {
    // Arrange
    const char* name = "Zhang San";
    float score = 88.5f;
    
    // Act
    int32_t result = add_student(name, score);
    
    // Assert
    EXPECT_GT(result, 0);  // 期望返回有效的学生ID
}

TEST_F(StudentManagerTest, TestCase2_AddStudent_InvalidName) {
    // Arrange
    const char* invalid_name = "";
    float score = 88.5f;
    
    // Act
    int32_t result = add_student(invalid_name, score);
    
    // Assert
    EXPECT_NE(result, 0);  // 期望返回错误
}

TEST_F(StudentManagerTest, TestCase3_AddStudent_InvalidScore) {
    // Arrange
    const char* name = "Li Si";
    float invalid_score = 101.0f;
    
    // Act
    int32_t result = add_student(name, invalid_score);
    
    // Assert
    EXPECT_NE(result, 0);  // 期望返回错误
}

TEST_F(StudentManagerTest, TestCase4_UpdateStudentScore_Valid) {
    // Arrange
    const char* name = "Wang Wu";
    float initial_score = 75.0f;
    int32_t student_id = add_student(name, initial_score);
    float new_score = 95.0f;
    
    // Act
    int32_t result = update_student_score(student_id, new_score);
    
    // Assert
    EXPECT_EQ(result, 0);
}

TEST_F(StudentManagerTest, TestCase5_UpdateStudentScore_InvalidId) {
    // Arrange
    int32_t invalid_id = -1;
    float new_score = 85.0f;
    
    // Act
    int32_t result = update_student_score(invalid_id, new_score);
    
    // Assert
    EXPECT_NE(result, 0);  // 期望返回错误
}

TEST_F(StudentManagerTest, TestCase6_UpdateStudentScore_InvalidScore) {
    // Arrange
    const char* name = "Zhao Liu";
    int32_t student_id = add_student(name, 80.0f);
    float invalid_score = -5.0f;
    
    // Act
    int32_t result = update_student_score(student_id, invalid_score);
    
    // Assert
    EXPECT_NE(result, 0);  // 期望返回错误
}

TEST_F(StudentManagerTest, TestCase7_GetAverageScore_NoStudents) {
    // Arrange
    db_init();
    
    // Act
    float result = get_average_score();
    
    // Assert
    EXPECT_NEAR(result, 0.0f, 0.01f);
}

TEST_F(StudentManagerTest, TestCase8_GetTotalStudents) {
    // Arrange
    add_student("Student1", 85.0f);
    add_student("Student2", 90.0f);
    
    // Act
    int32_t result = get_total_students();
    
    // Assert
    EXPECT_GE(result, 2);
}
