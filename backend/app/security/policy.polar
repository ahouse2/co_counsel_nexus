actor Principal {}

has_all_scopes(_actor, []) if true;
has_all_scopes(actor: Principal, [scope, *rest]) if actor.has_scope(scope) and has_all_scopes(actor, rest);

has_any_role(_actor, []) if false;
has_any_role(actor: Principal, [role, *rest]) if actor.has_role(role) or has_any_role(actor, rest);

allow(actor: Principal, action, resource: ResourceDescriptor) if
    resource.action == action and
    has_all_scopes(actor, resource.required_scopes) and
    (resource.allowed_roles matches [] or has_any_role(actor, resource.allowed_roles)) and
    (resource.tenant_id == nil or actor.tenant_id == resource.tenant_id);
