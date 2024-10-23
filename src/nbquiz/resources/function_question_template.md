{{question}}

Function definition: 

- Name: `{{name}}`
- Arguments:
{% for key in annotations %}
{% if key != "return" %}
  - `{{ key }}` (*`{{ annotations[key].__name__ }}`*)
{% endif %}
{% endfor %}
- Returns:  *`{{ annotations["return"].__name__ }}`*

Add the tag: `{{ celltag }}`
