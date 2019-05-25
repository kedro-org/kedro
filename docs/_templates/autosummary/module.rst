{{ fullname | escape | underline }}

.. rubric:: Description

.. automodule:: {{ fullname }}

   {% block public_modules %}
   {% if public_modules %}
   .. rubric:: Modules

   .. autosummary::
      :toctree:
      :template: autosummary/module.rst
   {% for item in public_modules %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block functions %}
   {% if functions %}
   .. rubric:: Functions

   .. autosummary::
      :toctree:
   {% for item in functions %}
      {%- if not item.startswith('_') %}
      {{ item }}
      {% endif %}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block classes %}
   {% if classes %}
   .. rubric:: Classes

   .. autosummary::
      :toctree:
      :template: autosummary/class.rst
   {% for item in classes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block exceptions %}
   {% if exceptions %}
   .. rubric:: Exceptions

   .. autosummary::
      :toctree:
      :template: autosummary/class.rst
   {% for item in exceptions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}
