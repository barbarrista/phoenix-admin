# Pretty Admin Panel Framework

## Project Roadmap

## Core Features

### FormView

- [x] Support FormView
- [x] Support form rendering
- [x] Support displaying JSON result
- [ ] Support displaying SimpleResult (message, description, urls)
- [x] Support StructureField (define field as Pydantic model and render depends form)

### JsonView

- [ ] Support JsonView (Send JSON in specific field)

### Support Error Display: Form Errors, Pydantic Validation Errors, 404 Errors

- [x] Form error rendering
- [x] Pydantic validation error handling
- [ ] Custom 404 page

### Support Middlewares

- [ ] Custom middleware
- [ ] Error handling middleware
- [ ] Middleware configuration

### Support Security/Authorization: AuthMiddleware, AuthProvider

- [x] Authentication middleware
- [x] Authorization providers
- [ ] Permission system
- [x] Keycloak auth
- [ ] CSRF Token

### Support hooks

- [ ] Before request
- [ ] After request
- [ ] After response

### Support Mounting to Another ASGI Framework

- [x] Mount AdminApp to another ASGI app

### Support Additional Templates

- [ ] Template discovery
- [ ] Template overrides
- [ ] Multiple template directories
- [ ] Template caching

### Support Additional Static Files

- [x] Static file serving
- [ ] Multiple static directories

### Support Serializers

- [ ] Pydantic
- [ ] MsgSpec
- [ ] Custom serializers

### Support exception handlers

- [ ] Custom exception handlers

### Support Lifespan

- [ ] Lifespan context manager

### Plugins

- [ ] Support Plugin architecture

### Localization

- [ ] Support i18n
