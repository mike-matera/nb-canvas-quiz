{{question}}

The cell should define the variables: 

{% for key in annotations %}
{% if key != "return" %}
  - `{{ key }}` (*`{{ annotations[key].__name__ }}`*)
{% endif %}
{% endfor %}

The result should be *`{{ annotations["return"].__name__ }}`*

Add the tag: `{{ celltag }}`
