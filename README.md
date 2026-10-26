# Pretty Admin Panel Framework

## Project Roadmap

## Core Features

### FormView

- [x] Support FormView
- [x] Support form rendering
- [x] Support displaying JSON result
- [ ] Support displaying SimpleResult (message, description, urls)
- [x] Support StructureField (define field as Pydantic model and render depends form)

### SqlalchemyModelView

CRUD for a SQLAlchemy 2 model. The async session comes from `SqlalchemyAsyncSessionExtension` (`request.state.db_session`). Working prototype: `__excluded__/sqla_test.py` (`UserView`, `SubdivisionView`, `RelationshipField`).

#### Already in place

- [x] `SqlalchemyModelView` registered by `identity`. `add_view` rejects a missing or empty `fields` and a duplicate `identity`
- [x] Routes `/{identity}/list`, `/detail/{ident}`, `/create`, `/update/{ident}`, `/api/{identity}`
- [x] List page: gridjs calls `GET /api/{identity}?limit&offset` and renders `{results, count}` (`PaginationResponseSchema`)
- [x] Columns from `fields` + `TableColumnProps`. `SqlalchemyMapper.to_json` returns values; `map_to_json` calls `to_html`, which escapes with `markupsafe.escape` (an email address is escaped before it is placed in `href`). A field with `mapper is None` still occupies one cell. List values are escaped item by item
- [x] `RelationshipField`: many-to-one uses `joinedload`, a collection (`uselist`) uses `selectinload`. An explicit `load_strategy` replaces the default. A `RelationshipField` pointed at a plain column raises `TypeError`. The label comes from the related view `repr_model`
- [x] `Pk.extract_value` for a column name, an `InstrumentedAttribute`, or a composite `list` / `tuple`. Each component is stringified before the values are joined. `Pk.columns` exposes those columns for `ORDER BY` and `COUNT`
- [x] When `get_list_stmt` has no `ORDER BY`, the list is ordered by the primary key, then paginated. An `ORDER BY` set on the statement is kept
- [x] `get_count` counts distinct primary-key rows. `ORDER BY`, `limit` and `offset` are dropped; `FROM` and `JOIN` from `get_list_stmt` stay, so a join does not inflate the count
- [x] A missing `limit` uses `page_limit`. `limit < 1` and `offset < 0` return 400. A `limit` above `ModelViewConfig.max_page_limit` (default 100) is clamped to that ceiling
- [x] A column is optional when it is nullable. A many-to-one relationship is optional when its foreign key is nullable. `required=True` forces the field to be required. `to_json` and `from_json` share this check. `NULL` in an optional column renders as `"-"`
- [x] `SqlalchemyMapper.from_json` awaits each field mapper, reads `field.name` when it is set and `source_field_name` otherwise, and stores the value under `source_field_name`. `RelationshipMapper.from_json` still raises `NotImplementedError`
- [x] Overridable `get_list_stmt`, `get_list`, `get_count`

Detail, create and update templates only print the title. `POST` on those actions raises `NotImplementedError`. There is no delete route. `Pk.parse` does not exist yet, so a URL segment cannot be turned back into a row.

#### 1. Primary key in the URL

`extract_value` serializes a key to a string (`id` or `id1,id2`). The reverse path does not exist, so detail/update cannot load a row.

- [ ] `Pk.parse(ident)` round-trips `extract_value`. A composite key segment must not contain a comma
- [ ] `get_one(session, ident)` selects by that PK and applies the same relationship load strategies as the list
- [ ] The list API always returns the PK, even when it is not a visible column, so a row can link to detail

#### 2. Detail

- [ ] `GET /{identity}/detail/{ident}` loads the row and renders it with `datagrid/grid.html`
- [ ] Missing row → 404
- [ ] `get_detail_stmt` is overridable, same way as `get_list_stmt`

#### 3. Create and update

Reuse the `form_fields/*` templates. `from_json` and column optionality are already in place; this step wires them to the create and update actions. `ModelViewConfig` has no `submit_button_text` today; the form can use a fixed "Save" until that field exists.

- [ ] `GET /create` renders an empty form. `GET /update/{ident}` fills it from `get_one`
- [ ] `POST` runs `SqlalchemyMapper.from_json`, then inserts or updates the row
- [ ] PK is omitted on create and readonly on update
- [ ] After a successful save, redirect to detail
- [ ] Validation errors render like `FormView` (`FormValidationError` next to the field). `IntegrityError` becomes a form error, not a traceback

#### 4. Relationships on the form

The list already shows a relationship label. The form cannot write one: `RelationshipMapper.from_json` raises `NotImplementedError`, and the widget is a plain select with no options.

- [ ] `from_json` accepts the related PK (or empty for NULL), loads the target through `model_view_registry[field.identity]`, and assigns the instance to the relationship attribute
- [ ] The select options are `(pk, repr_model)` from the related view
- [ ] A nullable relationship gets an empty option

A FK column without a relationship stays a normal field (`TextField(source_field=UserORM.subdivision_id)`).

#### 5. Delete

- [ ] `POST /{identity}/delete/{ident}`
- [ ] Confirm control on the detail page
- [ ] `delete_model(session, model)` hook, then `session.delete`
- [ ] Redirect to the list

#### 6. Fields per page

One `fields` tuple is the default for list, detail, create and update. The prototype sketches per-action mappers (`list_mapper`, `detail_mapper`, `create_mapper`, `update_mapper`); those are optional overrides, not a requirement for basic CRUD.

- [ ] Optional `list_fields` / `detail_fields` / `create_fields` / `update_fields`: names of fields from `fields`. Missing override means "all fields"
- [ ] A custom mapper on the view replaces `SqlalchemyMapper` only for the action that needs different serialization

#### 7. Sort and search

Pages are already stable: the list is ordered by the primary key unless `get_list_stmt` sets its own `ORDER BY`. `list.html` also turns on gridjs `sort` and `search` while pagination is server-side. Those controls never reach `/api/{identity}`, so they only reorder or filter the current page.

- [ ] `sort` and `order` query params, applied in `get_list_stmt`, only for columns with `column_props.sort`
- [ ] `q` query param against an explicit `search_fields` list
- [ ] Client-side search stays off until `q` is implemented
- [ ] Actions column: open, edit, delete. Flags on `ModelViewConfig`: `can_create`, `can_edit`, `can_delete`, `can_view_details` (all true by default)

#### 8. Session

`SqlalchemyAsyncSessionExtension` opens a session and does not commit or roll back. Reads work. Writes will not persist.

- [ ] On the way out of `on_request`: commit when the response succeeded and the session has new, dirty or deleted objects; roll back on exception
- [ ] A failed write does not leave the connection in a transaction

#### 9. Example

- [ ] `examples/sqla`: the User / Subdivision views from the prototype, with a DSN from the environment (no credentials in the repo)
- [ ] List, detail, create, update, delete, and one relationship select

#### Later

Permissions, CSRF, filters beyond a single `q`, bulk actions, inline edit. `before_create` / `after_update` hooks land after create, update and delete exist. Until then the extension points are `get_list_stmt`, `get_list`, `get_one`, `get_detail_stmt` and `delete_model`.

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
