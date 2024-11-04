{{question}}

Function definition: 

- Name: {{ name | literal }}
- Arguments: 
{% for key in annotations %}
{% if key != "return" %}
  - {{ key | literal }} (*`{{ annotations[key].__name__ }}`*)
{% endif %}
{% endfor %}
{% if annotations["return"] %}
- Returns:  *`{{ annotations["return"].__name__ }}`*
{% endif %}

Add the tag: `{{ celltag }}`
