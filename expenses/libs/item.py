# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe


# [Type]
def reload_items_of_types(types):
    names = get_items_of_types(types)
    if not names:
        return 0
    
    from .background import (
        uuid_key,
        is_job_running
    )
    
    job = uuid_key(names)
    job = f"reload-items-{job}"
    if not is_job_running(job):
        from .background import enqueue_job
        
        enqueue_job(
            "expenses.libs.item.reload_items",
            job,
            names=names
        )


# [Internal]
def get_items_of_types(types):
    dt = "Expense Item"
    names = frappe.get_list(
        dt,
        fields=["name"],
        filters=[[dt, "expense_type", "in", types]],
        pluck="name",
        ignore_permissions=True,
        strict=False
    )
    if not names or not isinstance(names, list):
        return 0
    
    return names


# [Internal]
def reload_items(names):
    from .cache import get_cached_doc
    
    dt = "Expense Item"
    for name in names:
        doc = get_cached_doc(dt, name)
        if doc:
            doc.reload_expense_accounts()


# [E Item Form]
@frappe.whitelist()
def search_item_types(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
    if filters:
        from .common import parse_json
        
        filters = parse_json(filters)
    
    if not filters or not isinstance(filters, dict):
        filters = {}
    
    from .type import query_types
    
    filters["is_group"] = 0
    return query_types(txt, filters, start, page_len, as_dict)


# [E Item, E Item Form]
@frappe.whitelist(methods=["POST"])
def get_type_accounts_list(type_name):
    if not type_name or not isinstance(type_name, str):
        return {"error": "Arguments required to get type accounts list are invalid."}
    
    from .account import get_type_accounts
    
    data = get_type_accounts(type_name, {
        "cost": 0.0,
        "min_cost": 0.0,
        "max_cost": 0.0,
        "qty": 0.0,
        "min_qty": 0.0,
        "max_qty": 0.0,
        "inherited": 1
    })
    if data is None:
        return {"error": "Expense type \"{0}\" doesn't exist.".format(type_name)}
    
    return data


# [Expense]
def get_item_company_account(item: str, company: str):
    from .cache import get_cache
    
    dt = "Expense Item"
    key = f"{item}-{company}-account-data"
    cache = get_cache(dt, key)
    if cache and isinstance(cache, dict):
        return cache
    
    from .account import get_item_company_account_data
    
    data = get_item_company_account_data(item, company)
    if not data:
        return {}
    
    from .cache import set_cache
    
    set_cache(dt, key, data)
    return data


# [E Exoense Form]
@frappe.whitelist()
def search_items(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
    if filters:
        from .common import parse_json
        
        filters = parse_json(filters)
    
    if (
        not filters or not isinstance(filters, dict) or
        not filters.get("company", "") or
        not isinstance(filters["company"], str)
    ):
        return []
    
    from .account import query_items_with_company_account
    from .search import (
        filter_search,
        prepare_data
    )
    from .type import get_types_filter_query
    
    dt = "Expense Item"
    doc = frappe.qb.DocType(dt)
    fqry = query_items_with_company_account(filters["company"])
    tqry = get_types_filter_query()
    qry = (
        frappe.qb.from_(doc)
        .select(
            doc.name.as_("label"),
            doc.name.as_("value")
        )
        .where(doc.disabled == 0)
        .where(doc.name.isin(fqry))
        .where(doc.expense_type.isin(tqry))
    )
    qry = filter_search(doc, qry, dt, txt, doc.name, "name")
    data = qry.run(as_dict=as_dict)
    data = prepare_data(data, dt, "name", txt, as_dict)
    return data