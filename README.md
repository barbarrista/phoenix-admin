# Pretty Admin Panel Framework

## Project Roadmap

## Core Features

### FormView

- [x] Support FormView
- [x] Support form rendering
- [ ] Support displaying JSON result
- [ ] Support displaying SimpleResult (message, description, urls)

### Support Error Display: Form Errors, Pydantic Validation Errors, 404 Errors

- [ ] Form error rendering
- [ ] Pydantic validation error handling
- [ ] Custom 404 page
- [ ] Error context propagation

### Support Middlewares

- [ ] Custom middleware
- [ ] Error handling middleware
- [ ] Middleware configuration

### Support Authorization: AuthMiddleware, AuthProvider

- [ ] Authentication middleware
- [ ] Authorization providers
- [ ] User session management
- [ ] Permission system
- [ ] JWT/OAuth support
- [ ] Keycloak auth

### Support Mounting to Another ASGI Framework

- [ ] Mount AdminApp to another ASGI app

### Support Additional Templates

- [ ] Template discovery
- [ ] Template overrides
- [ ] Multiple template directories
- [ ] Template caching

### Support Additional Static Files

- [ ] Static file serving
- [ ] Multiple static directories

### Support Serializers

- [ ] Pydantic
- [ ] MsgSpec
- [ ] Custom serializers

### Support Lifespan

- [ ] Lifespan context manager

### Plugins

- [ ] Support Plugin architecture
