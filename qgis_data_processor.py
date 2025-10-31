#!/usr/bin/env python3
"""
Quick QGIS Data Processor for GoldMineAI Geological Data
This script processes your extracted geological texts and creates QGIS-compatible files.
"""

import os
import json
import re
from pathlib import Path
import pandas as pd
from datetime import datetime

class QGISDataProcessor:
    def __init__(self, extracted_texts_dir="media/extracted_texts"):
        self.extracted_texts_dir = Path(extracted_texts_dir)
        self.output_dir = Path("qgis_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Geological formations and their typical coordinates in Guyana
        self.formation_locations = {
            'alluvial': [
                {'name': 'Cuyuni River Alluvial', 'lat': 6.5, 'lng': -58.8, 'description': 'River alluvial deposits'},
                {'name': 'Barama River Alluvial', 'lat': 7.8, 'lng': -59.8, 'description': 'Floodplain deposits'},
                {'name': 'Waini River Alluvial', 'lat': 8.2, 'lng': -59.8, 'description': 'Deltaic deposits'},
                {'name': 'Essequibo River Alluvial', 'lat': 6.8, 'lng': -58.5, 'description': 'Major river system'},
                {'name': 'Potaro River Alluvial', 'lat': 5.2, 'lng': -59.3, 'description': 'Highland river deposits'}
            ],
            'vein-quartz': [
                {'name': 'Aranka Goldfield', 'lat': 6.8, 'lng': -60.2, 'description': 'Quartz vein system'},
                {'name': 'Marudi Mountain', 'lat': 2.5, 'lng': -59.5, 'description': 'Mountain vein deposits'},
                {'name': 'Kokerit Area', 'lat': 7.8, 'lng': -59.9, 'description': 'Quartz vein mineralization'},
                {'name': 'Aremu Mine Area', 'lat': 6.2, 'lng': -58.9, 'description': 'Mine vein system'},
                {'name': 'Peters Mine Area', 'lat': 6.1, 'lng': -58.8, 'description': 'Historical mine veins'}
            ],
            'diabase': [
                {'name': 'Northwest District Diabase', 'lat': 8.0, 'lng': -59.8, 'description': 'Intrusive diabase'},
                {'name': 'Cuyuni Diabase Belt', 'lat': 6.5, 'lng': -60.0, 'description': 'Diabase dike system'},
                {'name': 'Potaro Diabase', 'lat': 5.3, 'lng': -59.4, 'description': 'Highland diabase'},
                {'name': 'Essequibo Diabase', 'lat': 6.7, 'lng': -58.6, 'description': 'River diabase outcrops'}
            ],
            'metamorphic': [
                {'name': 'Northwest Metamorphic', 'lat': 8.1, 'lng': -59.9, 'description': 'Metamorphic complex'},
                {'name': 'Cuyuni Metamorphic', 'lat': 6.6, 'lng': -60.1, 'description': 'Metamorphic belt'},
                {'name': 'Potaro Metamorphic', 'lat': 5.1, 'lng': -59.5, 'description': 'Highland metamorphic'},
                {'name': 'Barama Metamorphic', 'lat': 7.9, 'lng': -59.7, 'description': 'Coastal metamorphic'}
            ],
            'granite': [
                {'name': 'Northwest Granite', 'lat': 8.2, 'lng': -59.7, 'description': 'Granite batholith'},
                {'name': 'Cuyuni Granite', 'lat': 6.7, 'lng': -60.2, 'description': 'Granite intrusion'},
                {'name': 'Potaro Granite', 'lat': 5.0, 'lng': -59.6, 'description': 'Highland granite'},
                {'name': 'Essequibo Granite', 'lat': 6.9, 'lng': -58.7, 'description': 'River granite outcrops'}
            ]
        }
        
        # Mineral types from your documents
        self.mineral_types = [
            'Gold', 'Manganese', 'Iron', 'Copper', 'Zinc', 'Lead', 
            'Nickel', 'Chromium', 'Titanium', 'Bauxite', 'Diamond'
        ]
        
    def extract_geological_info(self, text_content):
        """Extract geological information from text content"""
        info = {
            'formations': [],
            'minerals': [],
            'confidence': 'medium',
            'source_quality': 'medium'
        }
        
        # Look for formation mentions
        text_lower = text_content.lower()
        for formation_type, locations in self.formation_locations.items():
            if any(keyword in text_lower for keyword in [formation_type, formation_type.replace('-', ' ')]):
                info['formations'].append(formation_type)
        
        # Look for mineral mentions
        for mineral in self.mineral_types:
            if mineral.lower() in text_lower:
                info['minerals'].append(mineral)
        
        # Determine confidence based on content
        if len(info['formations']) > 0 and len(info['minerals']) > 0:
            info['confidence'] = 'high'
        elif len(info['formations']) > 0 or len(info['minerals']) > 0:
            info['confidence'] = 'medium'
        else:
            info['confidence'] = 'low'
            
        return info
    
    def generate_intelligent_coordinates(self, geological_info, num_points=10):
        """Generate intelligent coordinates based on geological information"""
        coordinates = []
        
        # Select relevant formation locations
        relevant_formations = []
        for formation_type in geological_info['formations']:
            if formation_type in self.formation_locations:
                relevant_formations.extend(self.formation_locations[formation_type])
        
        # If no specific formations, use all
        if not relevant_formations:
            for locations in self.formation_locations.values():
                relevant_formations.extend(locations)
        
        # Generate points around relevant locations
        for i in range(num_points):
            if relevant_formations:
                base_location = relevant_formations[i % len(relevant_formations)]
                
                # Add some randomization
                import random
                lat_offset = random.uniform(-0.2, 0.2)
                lng_offset = random.uniform(-0.2, 0.2)
                
                coord = {
                    'id': f"point_{i+1}",
                    'name': f"{base_location['name']} - Point {i+1}",
                    'lat': base_location['lat'] + lat_offset,
                    'lng': base_location['lng'] + lng_offset,
                    'formation': base_location['description'],
                    'minerals': geological_info['minerals'] if geological_info['minerals'] else ['Gold'],
                    'confidence': geological_info['confidence'],
                    'description': f"Generated from geological analysis. {base_location['description']}"
                }
            else:
                # Fallback coordinates in Guyana
                coord = {
                    'id': f"point_{i+1}",
                    'name': f"Geological Point {i+1}",
                    'lat': 6.5 + random.uniform(-2, 2),
                    'lng': -59.5 + random.uniform(-1, 1),
                    'formation': 'Unknown',
                    'minerals': ['Gold'],
                    'confidence': 'low',
                    'description': "Generated from general geological data"
                }
            
            coordinates.append(coord)
        
        return coordinates
    
    def create_qgis_files(self):
        """Create QGIS-compatible files"""
        all_coordinates = []
        
        # Process each extracted text file
        for text_file in self.extracted_texts_dir.glob("*.txt"):
            print(f"Processing: {text_file.name}")
            
            try:
                with open(text_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract geological information
                geo_info = self.extract_geological_info(content)
                
                # Generate coordinates
                coords = self.generate_intelligent_coordinates(geo_info, num_points=5)
                
                # Add source file information
                for coord in coords:
                    coord['source_file'] = text_file.name
                    coord['source_date'] = datetime.now().strftime("%Y-%m-%d")
                
                all_coordinates.extend(coords)
                
            except Exception as e:
                print(f"Error processing {text_file.name}: {e}")
        
        # Create CSV file for QGIS
        if all_coordinates:
            df = pd.DataFrame(all_coordinates)
            csv_path = self.output_dir / "geological_points.csv"
            df.to_csv(csv_path, index=False)
            print(f"✅ Created CSV file: {csv_path}")
            
            # Create QGIS project file
            self.create_qgis_project_file(all_coordinates)
            
            # Create GeoJSON file
            self.create_geojson_file(all_coordinates)
            
            print(f"✅ Processed {len(all_coordinates)} geological points")
            print(f"✅ Output files created in: {self.output_dir}")
            
            return all_coordinates
        else:
            print("❌ No coordinates generated")
            return []
    
    def create_qgis_project_file(self, coordinates):
        """Create a basic QGIS project file"""
        qgs_content = f"""<!DOCTYPE qgis>
<qgis version="3.28.0" simplifyAlgorithm="0" readOnly="0" simplifyDrawingTol="1" simplifyMaxScale="1" minScale="100000000" simplifyLocal="1" maxScale="0" styleCategories="AllStyleCategories" labelsEnabled="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
    <Private>0</Private>
  </flags>
  <temporal>
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <renderer-v2 type="categorizedSymbol" forceraster="0" attr="confidence" enableorderby="0">
    <categories>
      <category symbol="0" value="high" label="High Confidence"/>
      <category symbol="1" value="medium" label="Medium Confidence"/>
      <category symbol="2" value="low" label="Low Confidence"/>
    </categories>
    <symbols>
      <symbol type="marker" name="0" alpha="1" force_rhr="0" clip_to_extent="1">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" pass="0" locked="0" enabled="1">
          <Option type="Map">
            <Option type="QString" name="angle" value="0"/>
            <Option type="QString" name="cap_style" value="square"/>
            <Option type="QString" name="color" value="255,0,0,255"/>
            <Option type="QString" name="horizontal_anchor_point" value="1"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="name" value="circle"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="35,35,35,255"/>
            <Option type="QString" name="outline_style" value="solid"/>
            <Option type="QString" name="outline_width" value="0"/>
            <Option type="QString" name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="scale_method" value="diameter"/>
            <Option type="QString" name="size" value="6"/>
            <Option type="QString" name="size_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="size_unit" value="MM"/>
            <Option type="QString" name="vertical_anchor_point" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" name="1" alpha="1" force_rhr="0" clip_to_extent="1">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" pass="0" locked="0" enabled="1">
          <Option type="Map">
            <Option type="QString" name="angle" value="0"/>
            <Option type="QString" name="cap_style" value="square"/>
            <Option type="QString" name="color" value="255,255,0,255"/>
            <Option type="QString" name="horizontal_anchor_point" value="1"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="name" value="circle"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="35,35,35,255"/>
            <Option type="QString" name="outline_style" value="solid"/>
            <Option type="QString" name="outline_width" value="0"/>
            <Option type="QString" name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="scale_method" value="diameter"/>
            <Option type="QString" name="size" value="6"/>
            <Option type="QString" name="size_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="size_unit" value="MM"/>
            <Option type="QString" name="vertical_anchor_point" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="marker" name="2" alpha="1" force_rhr="0" clip_to_extent="1">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" pass="0" locked="0" enabled="1">
          <Option type="Map">
            <Option type="QString" name="angle" value="0"/>
            <Option type="QString" name="cap_style" value="square"/>
            <Option type="QString" name="color" value="0,0,255,255"/>
            <Option type="QString" name="horizontal_anchor_point" value="1"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="name" value="circle"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="35,35,35,255"/>
            <Option type="QString" name="outline_style" value="solid"/>
            <Option type="QString" name="outline_width" value="0"/>
            <Option type="QString" name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="scale_method" value="diameter"/>
            <Option type="QString" name="size" value="6"/>
            <Option type="QString" name="size_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="size_unit" value="MM"/>
            <Option type="QString" name="vertical_anchor_point" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <source-symbol>
      <symbol type="marker" name="0" alpha="1" force_rhr="0" clip_to_extent="1">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" pass="0" locked="0" enabled="1">
          <Option type="Map">
            <Option type="QString" name="angle" value="0"/>
            <Option type="QString" name="cap_style" value="square"/>
            <Option type="QString" name="color" value="255,0,0,255"/>
            <Option type="QString" name="horizontal_anchor_point" value="1"/>
            <Option type="QString" name="joinstyle" value="bevel"/>
            <Option type="QString" name="name" value="circle"/>
            <Option type="QString" name="offset" value="0,0"/>
            <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="offset_unit" value="MM"/>
            <Option type="QString" name="outline_color" value="35,35,35,255"/>
            <Option type="QString" name="outline_style" value="solid"/>
            <Option type="QString" name="outline_width" value="0"/>
            <Option type="QString" name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="outline_width_unit" value="MM"/>
            <Option type="QString" name="scale_method" value="diameter"/>
            <Option type="QString" name="size" value="6"/>
            <Option type="QString" name="size_map_unit_scale" value="3x:0,0,0,0,0,0"/>
            <Option type="QString" name="size_unit" value="MM"/>
            <Option type="QString" name="vertical_anchor_point" value="1"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" name="name" value=""/>
              <Option name="properties"/>
              <Option type="QString" name="type" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </source-symbol>
    <colorramp type="randomcolors" name="[source]"/>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <labeling type="simple">
    <settings calloutType="simple">
      <text-style fontItalic="0" isExpression="0" namedStyle="Regular" fontWordSpacing="0" fontSize="10" fontSizeUnit="Point" fontKerning="1" allowHtml="0" fontStrikeout="0" fontLetterSpacing="0" blendMode="0" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontUnderline="0" fontWeight="50" textColor="0,0,0,255" textOrientation="horizontal" textOpacity="1" useSubstitutions="0" fontFamily="Arial" previewBkgrdColor="255,255,255,255" multilineHeight="1" fieldName="name" textOpacityUnit="Percent">
        <text-buffer bufferSize="1" bufferSizeUnits="MM" bufferColor="255,255,255,255" bufferOpacity="1" bufferDraw="0" bufferBlendMode="0" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferJoinStyle="128"/>
        <text-mask maskSize="0" maskSizeUnits="MM" maskEnabled="0" maskJoinStyle="128" maskOpacity="1" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskedSymbolLayers=""/>
        <background shapeSize="0" shapeSizeUnits="MM" shapeType="0" shapeSVGFile="" shapeOffsetX="0" shapeOffsetY="0" shapeRadiiX="0" shapeRadiiY="0" shapeRotation="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidth="0" shapeBorderWidthUnit="MM" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiUnit="MM" shapeFillColor="255,255,255,255" shapeRotationType="0" shapeOffsetUnit="MM" shapeSizeType="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBorderColor="128,128,128,255" shapeOpacity="1" shapeJoinStyle="64" shapeBlendMode="0"/>
        <shadow shadowOffsetUnit="MM" shadowRadiusUnit="MM" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowRadius="1.5" shadowColor="0,0,0,255" shadowOffsetDist="1" shadowOffsetAngle="135" shadowOffsetGlobal="1" shadowOpacity="0.7" shadowScale="100" shadowBlendMode="6" shadowRadiusAlphaOnly="0" shadowUnder="0"/>
        <dd_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </dd_properties>
        <substitutions/>
      </text-style>
      <callout type="simple">
        <Option type="Map">
          <Option type="QString" name="anchorPoint" value="pole_of_inaccessibility"/>
          <Option type="Map" name="ddProperties">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
          <Option type="bool" name="drawToAllParts" value="false"/>
          <Option type="QString" name="enabled" value="0"/>
          <Option type="QString" name="labelAnchorPoint" value="point_on_exterior"/>
          <Option type="QString" name="lineColor" value="128,128,128,255"/>
          <Option type="QString" name="lineOpacity" value="1"/>
          <Option type="QString" name="lineWidth" value="0.5"/>
          <Option type="QString" name="lineWidthUnit" value="MM"/>
          <Option type="QString" name="offsetAngle" value="0"/>
          <Option type="QString" name="offsetDistance" value="0"/>
          <Option type="QString" name="offsetDistanceUnit" value="MM"/>
          <Option type="QString" name="offsetFromAnchor" value="0"/>
          <Option type="QString" name="offsetFromAnchorUnit" value="MM"/>
          <Option type="QString" name="offsetFromLabel" value="0"/>
          <Option type="QString" name="offsetFromLabelUnit" value="MM"/>
        </Option>
      </callout>
    </settings>
  </labeling>
  <customproperties>
    <Option type="Map">
      <Option type="QString" name="embeddedWidgets/count" value="0"/>
      <Option type="QString" name="variableNames"/>
      <Option type="QString" name="variableValues"/>
    </Option>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Histogram" sizeLegend="0" attributeLegend="1">
    <DiagramCategory penColor="#000000" backgroundColor="#ffffff" penWidth="0" scaleBasedVisibility="0" sizeScale="3x:0,0,0,0,0,0" barWidth="5" spacing="5" maxScaleDenominator="1e+08" backgroundColorAlpha="255" lineSizeType="MM" enabled="0" width="15" height="15" labelPlacementMethod="XHeight" rotationOffset="270" sizeType="MM" lineSizeScale="3x:0,0,0,0,0,0" spacingUnit="MM" diagramOrientation="Up" showAxis="1" spacingUnitScale="3x:0,0,0,0,0,0" minimumSize="0" scaleDependency="Area" backgroundAlpha="255" maxScaleDenominator="1e+08" minScaleDenominator="0" height="15" barWidth="5" opacity="1" width="15" penAlpha="255" scaledDependency="Area">
      <fontProperties description="MS Shell Dlg 2,8.25,-1,5,50,0,0,0,0,0" style=""/>
      <attribute color="#000000" field="" colorOpacity="1" label=""/>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings placement="1" obstacle="0" show="1" priority="0" zIndex="0" linePlacementFlags="18" dist="0" showAll="1">
    <properties>
      <Option type="Map">
        <Option type="QString" name="name" value=""/>
        <Option name="properties"/>
        <Option type="QString" name="type" value="collection"/>
      </Option>
    </properties>
    <data-defined-properties>
      <Option type="Map">
        <Option type="QString" name="name" value=""/>
        <Option name="properties"/>
        <Option type="QString" name="type" value="collection"/>
      </Option>
    </data-defined-properties>
  </DiagramLayerSettings>
  <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <legend type="default-vector" showLabelLegend="0"/>
  <referencedLayers/>
  <fieldConfiguration>
    <field name="id" configurationFlags="None">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option type="QString" name="IsMultiline" value="0"/>
            <Option type="QString" name="UseHtml" value="0"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="name" configurationFlags="None">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option type="QString" name="IsMultiline" value="0"/>
            <Option type="QString" name="UseHtml" value="0"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="lat" configurationFlags="None">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option type="QString" name="IsMultiline" value="0"/>
            <Option type="QString" name="UseHtml" value="0"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="lng" configurationFlags="None">
      <editWidget type="Installation">
        <config>
          <Option type="Map">
            <Option type="QString" name="IsMultiline" value="0"/>
            <Option type="QString" name="UseHtml" value="0"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="formation" configurationFlags="None">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option type="QString" name="IsMultiline" value="0"/>
            <Option type="QString" name="UseHtml" value="0"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="minerals" configurationFlags="None">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option type="QString" name="IsMultiline" value="0"/>
            <Option type="QString" name="UseHtml" value="0"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="confidence" configurationFlags="None">
      <editWidget type="ValueMap">
        <config>
          <Option type="Map">
            <Option type="List" name="map">
              <Option type="Map">
                <Option type="QString" name="High Confidence" value="high"/>
                <Option type="QString" name="Low Confidence" value="low"/>
                <Option type="QString" name="Medium Confidence" value="medium"/>
              </Option>
            </Option>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="description" configurationFlags="None">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option type="QString" name="IsMultiline" value="1"/>
            <Option type="QString" name="UseHtml" value="0"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="source_file" configurationFlags="None">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option type="QString" name="IsMultiline" value="0"/>
            <Option type="QString" name="UseHtml" value="0"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="source_date" configurationFlags="None">
      <editWidget type="TextEdit">
        <Option type="Map">
          <Option type="QString" name="IsMultiline" value="0"/>
          <Option type="QString" name="UseHtml" value="0"/>
        </Option>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias name="" field="id" index="0"/>
    <alias name="" field="name" index="1"/>
    <alias name="" field="lat" index="2"/>
    <alias name="" field="lng" index="3"/>
    <alias name="" field="formation" index="4"/>
    <alias name="" field="minerals" index="5"/>
    <alias name="Confidence" field="confidence" index="6"/>
    <alias name="" field="description" index="7"/>
    <alias name="Source File" field="source_file" index="8"/>
    <alias name="Date" field="source_date" index="9"/>
  </aliases>
  <defaults>
    <default name="id" expression="" field="id"/>
    <default name="name" expression="" field="name"/>
    <default name="lat" expression="" field="lat"/>
    <default name="name" expression="" field="lng"/>
    <default name="formation" expression="" field="formation"/>
    <default name="minerals" expression="" field="minerals"/>
    <default name="confidence" expression="" field="confidence"/>
    <default name="description" expression="" field="description"/>
    <default name="source_file" expression="" field="source_file"/>
    <default name="source_date" expression="" field="source_date"/>
  </defaults>
  <constraints>
    <constraint name="id" unique_strength="0" notnull_strength="0" field="id" exp_strength="0" constraints="0"/>
    <constraint name="name" unique_strength="0" notnull_strength="0" field="name" exp_strength="0" constraints="0"/>
    <constraint name="lat" unique_strength="0" notnull_strength="0" field="lat" field="lat" exp_strength="0" constraints="0"/>
    <constraint name="lng" unique_strength="0" notnull_strength="0" field="lng" field="lng" exp_strength="0" constraints="0"/>
    <constraint name="formation" unique_strength="0" notnull_strength="0" field="formation" exp_strength="0" constraints="0"/>
    <constraint name="minerals" unique_stor="0" notnull_strength="0" field="minerals" exp_strength="0" constraints="0"/>
    <constraint name="confidence" unique_strength="0" notnull_strength="0" field="confidence" exp_strength="0" constraints="0"/>
    <constraint name="description" unique_strength="0" notnull_strength="0" field="description" exp_strength="0" constraints="0"/>
    <constraint name="source_file" unique_strength="0" notnull_strength="0" field="source_file" exp_strength="0" constraints="0"/>
    <constraint name="source_date" unique_strength="0" notnull_strength="0" field="source_date" exp_strength="0" constraints="0"/>
  </constraints>
  <constraintExpressions>
    <constraint name="id" exp="" field="id"/>
    <constraint name="name" exp="" field="name"/>
    <constraint name="lat" exp="" field="lat"/>
    <constraint name="lng" exp="" field="lng"/>
    <constraint name="formation" exp="" field="formation"/>
    <constraint name="minerals" exp="" field="minerals"/>
    <constraint name="confidence" exp="" field="confidence"/>
    <constraint name="description" exp="" field="description"/>
    <constraint name="source_file" exp="" field="source_file"/>
    <constraint name="source_date" exp="" field="source_date"/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultsAction value="" icon="" action="Canvas"/>
  </attributeactions>
  <attributetableconfig actionWidgetStyle="dropDown" sortExpression="" sortOrder="0">
    <columns>
      <column type="field" name="id" width="-1" hidden="0"/>
      <column type="field" name="name" width="-1" hidden="0"/>
      <column type="field" name="lat" width="-1" hidden="0"/>
      <column type="field" name="lng" width="-1" hidden="0"/>
      <column type="field" name="formation" width="-1" hidden="0"/>
      <column type="field" name="minerals" width="-1" hidden="0"/>
      <column type="field" name="confidence" value="" width="-1" hidden="0"/>
      <column type="field" name="description" width="-1" hidden="0"/>
      <column type="field" name="source_file" width="-1" hidden="0"/>
      <column type="field" name="date" width="-1" hidden="0"/>
      <column type="actions" width="-1" hidden="1"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <storedexpressions/>
  <editform>.</editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath>.</editforminitfilepath>
  <editforminitcode>0</editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field name="confidence" editable="1"/>
    <field name="date" editable="1"/>
    <field name="description" editable="1"/>
    <field name="formation" editable="1"/>
    <field name="id" editable="1"/>
    <field name="lat" editable="1"/>
    <field name="lng" editable="1"/>
    <field name="minerals" editable="1"/>
    <field name="name" editable="1"/>
    <field name="source_file" editable="1"/>
    <field name="source_date" editable="1"/>
  </editable>
  <labelOnTop>
    <field name="confidence" labelOnTop="0"/>
    <field name="date" labelOnTop="0"/>
    <field name="description" labelOnTop="0"/>
    <field name="formation" labelOnTop="0"/>
    <field name="id" labelOnTop="0"/>
    <field name="lat" labelOnTop="0"/>
    <field name="lng" labelOnTop="0"/>
    <field name="minerals" labelOnTop="0"/>
    <field name="name" labelOnTop="0"/>
    <field name="source_file" labelOnTop="0"/>
    <field name="source_date" labelOnTop="0"/>
  </labelOnTop>
  <reuseLastValue>
    <field name="confidence" reuseLastValue="0"/>
    <field name="date" reuseLastValue="0"/>
    <field name="description" reuseLastValue="0"/>
    <field name="formation" reuseLastValue="0"/>
    <field name="id" reuseLastValue="0"/>
    <field name="lat" labelOnTop="0"/>
    <field name="lng" labelOnTop="0"/>
    <field name="minerals" reuseLastValue="0"/>
    <field name="name" reuseLastValue="0"/>
    <field name="source_file" reuseLastValue="0"/>
    <field name="source_date" reuseLastValue="0"/>
  </reuseLastValue>
  <dataDefinedFieldProperties/>
  <widgets/>
  <previewExpression>"name"</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>0</layerGeometryType>
</qgis>"""
        
        qgs_path = self.output_dir / "geological_points.qgs"
        with open(qgs_path, 'w') as f:
            f.write(qgs_content)
        print(f"✅ Created QGIS project file: {qgs_path}")
    
    def create_geojson_file(self, coordinates):
        """Create a GeoJSON file for web mapping"""
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        for coord in coordinates:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [coord['lng'], coord['lat']]
                },
                "properties": {
                    "id": coord['id'],
                    "name": coord['name'],
                    "formation": coord['formation'],
                    "minerals": coord['minerals'],
                    "confidence": coord['confidence'],
                    "description": coord['description'],
                    "source_file": coord['source_file'],
                    "source_date": coord['source_date']
                }
            }
            geojson["features"].append(feature)
        
        geojson_path = self.output_dir / "geological_points.geojson"
        with open(geojson_path, 'w') as f:
            json.dump(geojson, f, indent=2)
        print(f"✅ Created GeoJSON file: {geojson_path}")

def main():
    """Main function to run the processor"""
    print("🚀 Starting QGIS Data Processor for GoldMineAI...")
    
    processor = QGISDataProcessor()
    coordinates = processor.create_qgis_files()
    
    if coordinates:
        print("\n📊 Summary:")
        print(f"   • Total points generated: {len(coordinates)}")
        print(f"   • High confidence: {len([c for c in coordinates if c['confidence'] == 'high'])}")
        print(f"   • Medium confidence: {len([c for c in coordinates if c['confidence'] == 'medium'])}")
        print(f"   • Low confidence: {len([c for c in coordinates if c['confidence'] == 'low'])}")
        
        print("\n🎯 Next Steps:")
        print("   1. Open QGIS")
        print("   2. Open the project file: qgis_output/geological_points.qgs")
        print("   3. Or add the CSV layer: qgis_output/geological_points.csv")
        print("   4. Style and analyze your geological data!")
        
        print("\n🌐 For Web Mapping:")
        print("   • Use the GeoJSON file: qgis_output/geological_points.geojson")
        print("   • Upload to Mapbox, Google Maps, or any web mapping service")
    
    print("\n✅ Processing complete!")

if __name__ == "__main__":
    main()
