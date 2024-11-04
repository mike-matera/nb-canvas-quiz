{{question}}

The cell should define the variables: 

{% for key in annotations %}
{% if key != "return" %}
  - {{ key | literal }} (*`{{ annotations[key].__name__ }}`*)
{% endif %}
{% endfor %}

{% if annotations["return"] %}
The result should be *`{{ annotations["return"].__name__ }}`*
{% endif %}

Add the tag: `{{ celltag }}`
