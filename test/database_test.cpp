#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "database.h"

using ::testing::Return;
using ::testing::_;

/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */

// database.c 中的函数不调用外部函数，无需Mock

/* ================================================= */

class DatabaseTest : public ::testing::Test {
protected:
    void SetUp() override {
        db_init();
    }
    
    void TearDown() override {
        db_init();  // Reset
    }
};

TEST_F(DatabaseTest, TestCase1_DbInit) {
    // Arrange
    // Setup already done in SetUp()
    
    // Act
    int32_t result = db_init();
    
    // Assert
    EXPECT_EQ(result, 0);
}

TEST_F(DatabaseTest, TestCase2_AddStudent) {
    // Arrange
    Student student = {1, "Alice", 95.5f};
    
    // Act
    int32_t result = db_add_student(&student);
    
    // Assert
    EXPECT_EQ(result, 0);
}

TEST_F(DatabaseTest, TestCase3_AddStudent_NullPointer) {
    // Arrange
    Student* null_student = NULL;
    
    // Act
    int32_t result = db_add_student(null_student);
    
    // Assert
    EXPECT_NE(result, 0);
}

TEST_F(DatabaseTest, TestCase4_GetStudent) {
    // Arrange
    Student student = {1, "Bob", 87.0f};
    db_add_student(&student);
    Student retrieved;
    
    // Act
    int32_t result = db_get_student(1, &retrieved);
    
    // Assert
    EXPECT_EQ(result, 0);
    EXPECT_EQ(retrieved.id, 1);
    EXPECT_EQ(retrieved.score, 87.0f);
}

TEST_F(DatabaseTest, TestCase5_GetStudent_NotFound) {
    // Arrange
    Student student = {1, "Charlie", 80.0f};
    db_add_student(&student);
    Student retrieved;
    
    // Act
    int32_t result = db_get_student(999, &retrieved);
    
    // Assert
    EXPECT_NE(result, 0);
}

TEST_F(DatabaseTest, TestCase6_UpdateScore) {
    // Arrange
    Student student = {1, "David", 75.0f};
    db_add_student(&student);
    
    // Act
    int32_t result = db_update_score(1, 88.5f);
    
    // Assert
    EXPECT_EQ(result, 0);
    Student retrieved;
    db_get_student(1, &retrieved);
    EXPECT_NEAR(retrieved.score, 88.5f, 0.01f);
}

TEST_F(DatabaseTest, TestCase7_DeleteStudent) {
    // Arrange
    Student student = {1, "Eve", 92.0f};
    db_add_student(&student);
    
    // Act
    int32_t result = db_delete_student(1);
    
    // Assert
    EXPECT_EQ(result, 0);
    Student retrieved;
    EXPECT_NE(db_get_student(1, &retrieved), 0);
}
