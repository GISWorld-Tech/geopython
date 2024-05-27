"""PyQGIS Mini project"""
from qgis.core import QgsVectorLayer, QgsProject, QgsVectorFileWriter, QgsApplication
from qgis.utils import iface
import processing


def relative_shp_path(file_name):
    return QgsProject.instance().readPath("./") + f'/geodata/{file_name}.shp'


def import_vector_layer(layer_path, layer_name):
    layer = QgsVectorLayer(layer_path, layer_name)
    return layer if layer.isValid() else None


def display_vector_layer(layer, name=None):
    displayed_layer = QgsProject.instance().addMapLayer(layer)
    if name:
        displayed_layer.setName(name)


def zoom_to_layer(layer):
    canvas = iface.mapCanvas()
    extent = layer.extent()
    canvas.setExtent(extent)
    canvas.refresh()


def export_shp_layer(layer, output_layer_path):
    QgsVectorFileWriter.writeAsVectorFormat(
        layer, output_layer_path, "utf-8", layer.crs(), driverName='ESRI Shapefile'
    )


def print_all_algo():
    for alg in QgsApplication.processingRegistry().algorithms():
        print(alg.id(), " --> ", alg.displayName())


def buffer(layer, distance, dissolve=False):
    param = {'DISSOLVE': dissolve, 'DISTANCE': distance, 'END_CAP_STYLE': 0,
             'INPUT': layer, 'JOIN_STYLE': 0,
             'MITER_LIMIT': 2,
             'OUTPUT': 'TEMPORARY_OUTPUT', 'SEGMENTS': 5}
    return processing.run("native:buffer", param)['OUTPUT']


def deselect_features(layer):
    layer.removeSelection()


def extract_selected_features(layer):
    param = {'INPUT': layer, 'OUTPUT': 'memory'}
    return processing.run("native:saveselectedfeatures", param)['OUTPUT']


def select_feature_by_expression(layer, expression='"fid" is not NULL', extract=False):
    layer.selectByExpression(expression)
    selected_features = list(layer.getSelectedFeatures())
    if extract:
        extracted_features = extract_selected_features(layer)
        deselect_features(layer)
        return extracted_features, len(selected_features)
    deselect_features(layer)
    return len(selected_features)


def select_feature_by_location(layer, intersected_layer, predicate_key='INTERSECT', extract=False):
    predicate = {
        'INTERSECT': 0, 'CONTAIN': 1, 'DISJOINT': 2, 'ARE_WITHIN': 6
    }
    param = {'INPUT': layer, 'INTERSECT': intersected_layer, 'METHOD': 0, 'PREDICATE': [predicate[predicate_key]]}
    processing.run('native:selectbylocation', param)['OUTPUT']
    selected_features = list(layer.getSelectedFeatures())

    if extract:
        extracted_feature = extract_selected_features(layer)
        deselect_features(layer)
        return extracted_feature, len(selected_features)
    deselect_features(layer)
    return len(selected_features)


def analyze_kindergarten_distribution(inner_buildings, outer_buildings, threshold):
    if outer_buildings > 0:
        print(f'There are {outer_buildings} buildings outside of the kindergarten buffer')
        if outer_buildings / inner_buildings < threshold:
            print('Sufficient')
        else:
            print(f'Not Sufficient. threshold: {threshold}, {outer_buildings / inner_buildings} ')
    else:
        print('No residential buildings outside of the buffer')


if __name__ == '__console__':
    layer_path = relative_shp_path('buildings')
    if import_vector_layer(layer_path, 'imported_buildings'):
        buildings = import_vector_layer(layer_path, 'imported_buildings')
        display_vector_layer(buildings)
        zoom_to_layer(buildings)

        # select kindergarten
        kindergarten_expression = '''
            "building" = 'kindergarten'
        '''

        kindergarten_building_layer, kindergarten_building_count = select_feature_by_expression(
            buildings, kindergarten_expression, True
        )
        print(f'number of kindergarten: {kindergarten_building_count}')

        # create buffer around selected kindergartens
        buffered_layer = buffer(kindergarten_building_layer, 300, True)

        # buildings inside and outside of kindergarten's buffered area
        residential_buildings_inside_buffer = select_feature_by_location(buildings, buffered_layer, 'ARE_WITHIN')
        residential_buildings_outside_buffer = select_feature_by_location(buildings, buffered_layer, 'DISJOINT')

        analyze_kindergarten_distribution(
            residential_buildings_inside_buffer, residential_buildings_outside_buffer, 0.2
        )
    else:
        print('layer is not valid')
