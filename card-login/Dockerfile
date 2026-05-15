# 1단계: 빌드 환경 (Java 17)
FROM openjdk:17-jdk-slim AS build
WORKDIR /app

# Maven 실행 파일과 소스코드 복사
COPY mvnw .
COPY .mvn .mvn
COPY pom.xml .
COPY src src

# 실행 권한 부여 및 빌드
RUN chmod +x mvnw
RUN ./mvnw clean package -DskipTests

# 2단계: 실행 환경
FROM openjdk:17-jdk-slim
WORKDIR /app

# 빌드된 jar 파일 복사
COPY --from=build /app/target/*.jar app.jar

# 포트 개방 및 실행
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]