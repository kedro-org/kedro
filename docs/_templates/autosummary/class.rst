{{ fullname | escape | underline }}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

   {% block attributes %}
   {% if attributes %}
   .. rubric:: Attributes

   .. autosummary::
      {% for item in all_attributes %}
      {%- if not item.startswith('_') %}
      {{ name }}.{{ item }}
      {%- endif -%}
      {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block methods %}
   {% if methods %}
   .. rubric:: Methods

   .. autosummary::
      {% for item in methods %}
      {{ name }}.{{ item }}
      {%- endfor %}
    {% endif %}
   {% endblock %}
