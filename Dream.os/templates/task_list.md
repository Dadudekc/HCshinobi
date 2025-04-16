# Task List: templates Module (`/d:/Dream.os/templates/`)

Tasks related to managing template files used for code generation, prompts, reports, etc.

## I. Template Inventory & Organization

-   [ ] **Catalog Templates:** List all template files (e.g., Jinja2, other formats) in `/d:/Dream.os/templates/`.
-   [ ] **Identify Usage:** Determine where each template is used (e.g., which agent, script, or reporting process).
-   [ ] **Organize Structure:** Ensure a clear directory structure or naming convention based on template usage.

## II. Template Content & Refinement

-   [ ] **Review Accuracy:** Verify templates generate the correct output structure and content.
-   [ ] **Refine Logic:** Improve template logic, parameter usage, and clarity.
-   [ ] **Consistency:** Ensure consistent style and formatting across related templates.

## III. Integration

-   [ ] **Verify Loading:** Check that modules using these templates (e.g., agents in `/d:/Dream.os/agents/`, reporting scripts) load them correctly.
-   [ ] **Parameter Passing:** Ensure all necessary parameters are correctly passed to the templates during rendering.
-   [ ] **Error Handling:** Review how errors during template rendering are handled by the calling code.

## IV. Testing

-   [ ] **Add Template Tests:** Create tests (unit or integration) that render templates with various inputs and validate the output.
-   [ ] **Test Edge Cases:** Include tests for missing parameters, invalid inputs, or complex template logic.

## V. Documentation

-   [ ] **Document Templates:** Add comments or documentation within templates explaining their purpose, parameters, and expected output.
-   [ ] **Summarize in Docs:** Consider summarizing template usage in `/d:/Dream.os/docs/task_list.md`.

## VI. Finalization

-   [ ] Commit changes to template files and related rendering logic.
-   [ ] Ensure templates are accurate, well-organized, and documented. 