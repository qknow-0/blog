# Java 单元测试：JUnit 5 不是唯一解

> 本文基于 Java 21、JUnit 5.11、Mockito 5.x。

Java 的测试生态是所有语言里最成熟的之一——不是因为它简单，而是因为它踩了足够多的坑。JUnit 从 3 到 5 花了二十年，Mockito 从 `expect()` 到 `when()` 重构了三次 API。这篇文章不是入门教程，是知道 JUnit 之后该看的东西。

## JUnit 5 的核心改进

JUnit 4 只有一个 `@Test`。JUnit 5 把它拆成了三层：

```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;

@DisplayName("Calculator")
class CalculatorTest {

    @Test
    @DisplayName("should add two positive numbers")
    void addsPositiveNumbers() {
        assertEquals(5, new Calculator().add(2, 3));
    }

    @Nested
    @DisplayName("when dividing")
    class Division {

        @Test
        @DisplayName("should throw on zero division")
        void throwsOnZeroDivision() {
            assertThrows(ArithmeticException.class,
                () -> new Calculator().divide(10, 0));
        }
    }
}
```

三个真正重要的变化：

**1. `@Nested` —— 测试内类结构**。和 Rust 的 `mod tests`、Go 的 `t.Run` 一样，JUnit 5 让测试文件内部按场景分组。IDE 里展开 Nested 类看到树状结构，比 JUnit 4 的平铺表好读得多。

**2. `@DisplayName` —— 可读文本替代方法名**。不要写 `testAddPositiveNumbers` 驼峰命名，用 `@DisplayName("should add two positive numbers")` —— 测试报告读起来像 spec 文档。

**3. Lambda 和 `assertThrows`** —— JUnit 4 的 `@Test(expected = X)` 绕不住异常抛出的确切时机。`assertThrows` 精确控制。

## 参数化测试：表驱动

JUnit 5 的参数化测试比 JUnit 4 好一个数量级：

```java
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.MethodSource;

@ParameterizedTest
@CsvSource({
    "2, 3, 5",
    "-1, -2, -3",
    "0, 0, 0",
    "-5, 10, 5"
})
void add_givesSum(int a, int b, int expected) {
    assertEquals(expected, new Calculator().add(a, b));
}
```

这是 Go 表驱动测试的 Java 版。多个 case 一个方法，少写 N 个 `@Test`。更复杂的用例用 `@MethodSource`：

```java
static Stream<Arguments> divisionCases() {
    return Stream.of(
        Arguments.of(10, 2, 5),
        Arguments.of(9, 3, 3),
        Arguments.of(0, 5, 0)
    );
}

@ParameterizedTest
@MethodSource("divisionCases")
void divide_validInput(int a, int b, int expected) {
    assertEquals(expected, new Calculator().divide(a, b));
}
```

`@MethodSource` 的工厂方法返回 `Stream<Arguments>`——它是 JUnit 5 动态测试的底层机制。所有 `@CsvSource`、`@ValueSource` 最终都编译成这种流。

## AssertJ：读得懂的断言

JUnit 的 `assertEquals(expected, actual)` 容易写反——参数顺序搞反了错误消息就反了。AssertJ 用链式断言：

```java
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

assertThat(calculator.add(2, 3))
    .isEqualTo(5)
    .isGreaterThan(0);

assertThat(users)
    .hasSize(3)
    .extracting(User::getName)
    .containsExactly("Alice", "Bob", "Charlie");

assertThatThrownBy(() -> calculator.divide(10, 0))
    .isInstanceOf(ArithmeticException.class)
    .hasMessageContaining("zero");
```

链式断言看起来像句子，IDE 自动补全知道你下个元素是什么类型。JUnit 自己的 `assertXXX` 行内补全只给了 `assertEquals(int, int)`——没有任何语义提示。AssertJ 对集合的 `extracting` 能一行映射字段然后断言，不用手写 `for` 循环。

## Mockito：为什么不要用 `any()` 随意匹配

Mockito 最常见的错误是滥用 `any()`：

```java
// 反例——垃圾 mock，什么参数都匹配
when(userRepo.findById(any())).thenReturn(Optional.of(testUser));

// 正确——精确 mock，只匹配这个 ID
when(userRepo.findById(eq(42L))).thenReturn(Optional.of(testUser));
```

`any()` 让测试看起来「通过了」但从来不验证参数——修改参数但测试不挂只是掩盖了问题。用 `eq()`、`argThat()` 精确匹配参数，mock 失败帮你发现参数变化。

Mockito 和 Spring Boot 的 `@MockBean` 是经典组合：

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock UserRepository userRepo;
    @InjectMocks UserService userService;

    @Test
    void getUser_returnsUser() {
        var user = new User(42L, "Alice");
        when(userRepo.findById(42L)).thenReturn(Optional.of(user));

        var result = userService.getUser(42L);
        assertThat(result.getName()).isEqualTo("Alice");

        verify(userRepo).findById(42L);  // 确认真的调用了
    }
}
```

`verify` 是 mock 的最终确认——不只是正确返回，而且正确调用。不写 verify 的 mock 隐藏了「应该调用但没调用的方法」——测试不报绿也不报错，但实际逻辑漏洞被掩盖了。

## 测试命名

JUnit 5 的 `@DisplayName` 让测试名从技术细节变成行为描述：

```java
// ❌ 技术细节——改了方法名就不匹配
void testAdd() { }

// ❌ 驼峰排版——德国同事很难读
void testAddPositiveNumbersAndNegativeNumbersWithZero() { }

// ✅ 行为描述
@DisplayName("should add positive numbers and return correct sum")
void addsPositiveNumbers() { }
```

原则是：测试名应该让不是这个项目的人也看得懂被测行为。代码 review 时按测试名的描述看下来——而不是看代码猜什么行为。

## 测试和 Spring Boot

Spring Boot 集成测试最痛苦的三个词：应用程序上下文启动时间。解决方案是分层：

```java
// 快速——纯单测，无 Spring
@ExtendWith(MockitoExtension.class)
@DisplayName("UserService (unit)")
class UserServiceUnitTest { /* mock 一切 */ }

// 中速——只加载需要的 slice
@WebMvcTest(UserController.class)
@DisplayName("UserController (web layer)")
class UserControllerTest { /* 只测 Controller 层 */ }

// 慢速——完整 Spring 容器，CI 上跑
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@DisplayName("UserAPI (integration)")
class UserIntegrationTest { /* 端到端 */ }
```

`@WebMvcTest` 只加载 Controller + MockMvc，不启动整个 ApplicationContext——启动时间从 5 秒降到 0.5 秒。`@DataJpaTest` 只加载 Repository 层 + 内嵌数据库。合理分层把测试从「全部一起五分钟」变成「80% 在 0.X 秒内完成」。

## 可复用设计

1. **AssertJ 链式断言替代 `assertEquals`** —— 读错消息的概率从 20% 降到 0%
2. **`@Nested` 分组组织场景** —— IDE 里就能看到测试结构
3. **`@MethodSource` 处理复杂参数表** —— 生成大量组合输入比手写 N 个方法强
4. **Mock 用 `verify` 确认调用** —— 返回值正确不等于调用正确
5. **Spring Boot 按层级选注解** —— 慢的集成测试不在 PR 每次 commit 时都跑

> 参考：[JUnit 5 用户指南](https://junit.org/junit5/docs/current/user-guide/) · [Mockito 文档](https://javadoc.io/doc/org.mockito/mockito-core/latest/org/mockito/Mockito.html) · [AssertJ 文档](https://assertj.github.io/doc/)
