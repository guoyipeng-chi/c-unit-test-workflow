#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "validator.h"

using ::testing::Return;
using ::testing::_;
using ::testing::AtLeast;

/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */

// 本文件中的validator.c函数不调用其他外部函数，所以无需Mock
// 但这里保留的模板展示如果需要Mock应该如何做：
// 
// 示例：如果validate_student_name需要调用strlen的自定义版本，
// 可在此处定义Mock：
// #define MOCK_STRLEN_RETURN_VALUE  64
// #define MOCK_STRLEN_CALLED_WITH   "student_name"

/* ================================================= */

class ValidatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 初始化测试前置条件
    }
    
    void TearDown() override {
        // 清理测试后续处理
    }
};

// Test Case 1: Test normal execution path
TEST_F(ValidatorTest, TestCase1_NormalCase) {
    // Arrange
    const char* valid_name = "John Doe";
    
    // Act
    int32_t result = validate_student_name(valid_name);
    
    // Assert
    EXPECT_EQ(result, 0);  // 期望成功返回0
}

// Test Case 2: Test boundary conditions
TEST_F(ValidatorTest, TestCase2_BoundaryCase) {
    // Arrange
    const char* boundary_name = "A";  // 最短有效名称
    
    // Act
    int32_t result = validate_student_name(boundary_name);
    
    // Assert
    EXPECT_EQ(result, 0);  // 期望成功返回0
}

// Test Case 3: Test error handling - empty string
TEST_F(ValidatorTest, TestCase3_ErrorCase_EmptyString) {
    // Arrange
    const char* empty_name = "";
    
    // Act
    int32_t result = validate_student_name(empty_name);
    
    // Assert
    EXPECT_NE(result, 0);  // 期望返回错误
}

// Test Case 4: Test error handling - NULL pointer
TEST_F(ValidatorTest, TestCase4_ErrorCase_NullPointer) {
    // Arrange
    const char* null_name = NULL;
    
    // Act
    int32_t result = validate_student_name(null_name);
    
    // Assert
    EXPECT_NE(result, 0);  // 期望返回错误
}

// Test Case 5: Test error handling - string too long
TEST_F(ValidatorTest, TestCase5_ErrorCase_TooLong) {
    // Arrange
    char long_name[100];
    memset(long_name, 'A', 99);
    long_name[99] = '\0';  // 超过63字符限制
    
    // Act
    int32_t result = validate_student_name(long_name);
    
    // Assert
    EXPECT_NE(result, 0);  // 期望返回错误
}

// ========== validate_score 函数的测试用例 ===========

class ValidateScoreTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

// Test Case 1: Valid score in middle range
TEST_F(ValidateScoreTest, TestCase1_ValidNormalScore) {
    // Arrange
    float valid_score = 85.5f;
    
    // Act
    int32_t result = validate_score(valid_score);
    
    // Assert
    EXPECT_EQ(result, 0);
}

// Test Case 2: Valid boundary scores
TEST_F(ValidateScoreTest, TestCase2_Valid_Boundary_Zero) {
    // Arrange
    float boundary_score = 0.0f;
    
    // Act
    int32_t result = validate_score(boundary_score);
    
    // Assert
    EXPECT_EQ(result, 0);
}

TEST_F(ValidateScoreTest, TestCase3_Valid_Boundary_Hundred) {
    // Arrange
    float boundary_score = 100.0f;
    
    // Act
    int32_t result = validate_score(boundary_score);
    
    // Assert
    EXPECT_EQ(result, 0);
}

// Test Case 4: Invalid negative score
TEST_F(ValidateScoreTest, TestCase4_Invalid_Negative) {
    // Arrange
    float invalid_score = -1.0f;
    
    // Act
    int32_t result = validate_score(invalid_score);
    
    // Assert
    EXPECT_NE(result, 0);
}

// Test Case 5: Invalid score above 100
TEST_F(ValidateScoreTest, TestCase5_Invalid_OverHundred) {
    // Arrange
    float invalid_score = 101.0f;
    
    // Act
    int32_t result = validate_score(invalid_score);
    
    // Assert
    EXPECT_NE(result, 0);
}

// ========== validate_student_id 函数的测试用例 ===========

class ValidateStudentIdTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

// Test Case 1: Valid ID
TEST_F(ValidateStudentIdTest, TestCase1_ValidId) {
    // Arrange
    int32_t valid_id = 1;
    
    // Act
    int32_t result = validate_student_id(valid_id);
    
    // Assert
    EXPECT_EQ(result, 0);
}

// Test Case 2: Large valid ID
TEST_F(ValidateStudentIdTest, TestCase2_LargeValidId) {
    // Arrange
    int32_t valid_id = 999999;
    
    // Act
    int32_t result = validate_student_id(valid_id);
    
    // Assert
    EXPECT_EQ(result, 0);
}

// Test Case 3: Invalid ID - zero
TEST_F(ValidateStudentIdTest, TestCase3_InvalidId_Zero) {
    // Arrange
    int32_t invalid_id = 0;
    
    // Act
    int32_t result = validate_student_id(invalid_id);
    
    // Assert
    EXPECT_NE(result, 0);
}

// Test Case 4: Invalid ID - negative
TEST_F(ValidateStudentIdTest, TestCase4_InvalidId_Negative) {
    // Arrange
    int32_t invalid_id = -1;
    
    // Act
    int32_t result = validate_student_id(invalid_id);
    
    // Assert
    EXPECT_NE(result, 0);
}
