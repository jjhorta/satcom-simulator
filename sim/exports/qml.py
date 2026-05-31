"""
sim/exports/qml.py — QGIS Layer Style (.qml) templates.

These styles make the exported GeoJSON files look professional
when opened in QGIS — no manual configuration needed.

Each function returns a .qml file path alongside the .geojson.
Copy the .qml next to the .geojson (same basename) and QGIS
auto-loads the style when you drag the file in.
"""

import os

HEATMAP_QML = """<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.28" styleCategories="AllStyleCategories" rendererType="graduatedSymbol">
  <renderer-v2 symbol="0" type="graduatedSymbol" graduatedMethod="GraduatedColor"
               attr="availability_pct" label="" enablemodebydefault="1">
    <ranges>
      <range symbol="0" lower="95.0" upper="100.0" label="Critical (&gt;95%)" render="true"/>
      <range symbol="1" lower="70.0" upper="95.0"  label="Premium (70-95%)" render="true"/>
      <range symbol="2" lower="50.0" upper="70.0"  label="Standard (50-70%)" render="true"/>
      <range symbol="3" lower="30.0" upper="50.0"  label="Basic (30-50%)" render="true"/>
      <range symbol="4" lower="10.0" upper="30.0"  label="Low (10-30%)" render="true"/>
      <range symbol="5" lower="0.0"  upper="10.0"  label="No Service (&lt;10%)" render="true"/>
    </ranges>
    <symbols>
      <symbol name="0" type="fill" alpha="1" clip_to_extent="1">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="0,230,0,255"/>
          <prop k="outline_style" v="no"/>
        </layer>
      </symbol>
      <symbol name="1" type="fill" alpha="1" clip_to_extent="1">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="120,230,0,255"/>
          <prop k="outline_style" v="no"/>
        </layer>
      </symbol>
      <symbol name="2" type="fill" alpha="1" clip_to_extent="1">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="230,230,0,255"/>
          <prop k="outline_style" v="no"/>
        </layer>
      </symbol>
      <symbol name="3" type="fill" alpha="1" clip_to_extent="1">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="230,120,0,255"/>
          <prop k="outline_style" v="no"/>
        </layer>
      </symbol>
      <symbol name="4" type="fill" alpha="1" clip_to_extent="1">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="230,60,0,255"/>
          <prop k="outline_style" v="no"/>
        </layer>
      </symbol>
      <symbol name="5" type="fill" alpha="1" clip_to_extent="1">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="200,0,0,255"/>
          <prop k="outline_style" v="no"/>
        </layer>
      </symbol>
    </symbols>
    <colorramp type="gradient" name="[source]">
      <Option type="Map">
        <Option name="color1" type="QColor" value="#c80000"/>
        <Option name="color2" type="QColor" value="#00e600"/>
      </Option>
    </colorramp>
    <source-symbol>
      <symbol name="0" type="fill" clip_to_extent="1">
        <layer pass="0" class="SimpleFill" locked="0">
          <prop k="color" v="128,128,128,255"/>
          <prop k="outline_style" v="no"/>
        </layer>
      </symbol>
    </source-symbol>
  </renderer-v2>
  <layerOpacity>0.7</layerOpacity>
  <blendMode>0</blendMode>
</qgis>
"""

ROUTE_QML = """<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.28" styleCategories="AllStyleCategories">
  <pipe>
    <rasterrenderer type="singlebandcolordata" band="1" opacity="1">
      <rastertransparency/>
    </rasterrenderer>
    <provider>ogr</provider>
  </pipe>
</qgis>
"""


def write_qml(geojson_path: str, style_type: str = "heatmap"):
    """Write a .qml file alongside the .geojson file.

    QGIS auto-loads the .qml when the .geojson is opened if they
    share the same basename in the same directory.

    Args:
        geojson_path: Path to the .geojson file
        style_type:   'heatmap', 'route', or 'coverage'
    """
    qml_path = os.path.splitext(geojson_path)[0] + ".qml"

    if style_type == "heatmap":
        content = HEATMAP_QML
    elif style_type == "route":
        content = ROUTE_QML
    else:
        content = HEATMAP_QML  # coverage uses same graduated style

    with open(qml_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  💾 QGIS style saved: {qml_path}")
    return qml_path
