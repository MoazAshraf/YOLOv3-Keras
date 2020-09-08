import numpy as np
import cv2


CLASS_NAME_TO_INDEX = {
    'aeroplane': 0, 'bicycle': 1, 'bird': 2, 'boat': 3, 'bottle': 4, 'bus': 5,
    'car': 6, 'cat': 7, 'chair': 8, 'cow': 9, 'diningtable': 10, 'dog': 11,
    'horse': 12, 'motorbike': 13, 'person': 14, 'pottedplant': 15, 'sheep': 16,
    'sofa': 17, 'train': 18, 'tvmonitor': 19
}
INDEX_TO_CLASS_NAME = list(CLASS_NAME_TO_INDEX.keys())

def preprocess_image(image, newsize=(448, 448)):
    """
    Resizes and normalizes the image
    """

    image = cv2.resize(image, newsize)
    image = image / 255.
    return image

def bndbox_to_coords(bndbox, img_width, img_height, s):
    """
    Given a bounding box in pixel coordinates, the image dimensions and the grid size (s),
    this function returns:

    - x, y: the center coordinates of the bounding box relative to the cell associated
            with the bounding box where (0, 0) is the top left of the cell and (1, 1)
            is the bottom right.
    - w, h: the size of the bounding box in grid units.
    - cell_x, cell_y: coordinates of the cell associated with the bounding box
    """

    xmin, xmax, ymin, ymax = bndbox

    # absolute position in grid units
    x = (xmin + xmax) / 2 / img_width * s
    y = (ymin + ymax) / 2 / img_height * s

    # size in grid units
    w = (xmax - xmin) / img_width * s
    h = (ymax - ymin) / img_height * s

    # position relative to cell
    cell_x, cell_y = int(x), int(y)
    x, y = (x - cell_x), (y - cell_y)

    return x, y, w, h, cell_x, cell_y

def coords_to_bndbox(x, y, w, h, cell_x, cell_y, img_width, img_height, s):
    """
    Given bounding box data in the format specified by bndbox_to_coords() as well as
    the image dimensions and the grid size (s), this function returns the bounding
    box in pixel coordinates as (xmin, xmax, ymin, ymax).
    """

    x = (x + cell_x) * img_width / s
    y = (y + cell_y) * img_height / s
    w = w * img_width / s
    h = h * img_height / s

    xmin = round(x - w / 2)
    xmax = round(x + w / 2)
    ymin = round(y - h / 2)
    ymax = round(y + h / 2)

    return xmin, xmax, ymin, ymax

def preprocess_label(label, s=7, b=2, c=20):
    """
    Creates a target label using a label dictionary

    - s is the size of the grid (there will be s*s cells)
    - b is the number of bounding boxes for each cell
    - c is the number of possible classes

    Note: for now this function only uses one bounding box per cell

    Returns an s * s * (b * 5 + c) such that each cell has a (b * 5 * c) vector with
    the following:
    - the confidence score of the object
    - the bounding box coordinates
    - one-hot encoding of the label classs
    """

    img_width, img_height = label['image-size']['width'], label['image-size']['height']

    label_shape = (s, s, b * 5 + c)
    label_tensor = np.zeros(label_shape)

    for object in label['objects']:
        # get object data
        class_index = CLASS_NAME_TO_INDEX[object['name']]
        x, y, w, h, cell_x, cell_y = bndbox_to_coords(object['bndbox'], img_width, img_height, s)

        # add the data to the tensor
        if label_tensor[cell_y, cell_x, 0] == 0:
            label_tensor[cell_y, cell_x, 0] = 1
            label_tensor[cell_y, cell_x, 1:5] = x, y, w, h
            label_tensor[cell_y, cell_x, 10+class_index] = 1
        
    return label_tensor

def tensor_to_label(label_tensor, img_width, img_height, img_depth=3):
    """
    Converts a tensor in the format specified in preprocess_label() to a label
    in the format specified by create_labels.create_object_detection_label()
    except that the 'difficult' property is omitted.
    """

    # get grid size
    s = label_tensor.shape[0]
    objects = []

    for cell_y in range(s):
        for cell_x in range(s):
            if label_tensor[cell_y, cell_x, 0] == 1:
                # get bounding box
                x, y, w, h = label_tensor[cell_y,cell_x,1:5]
                xmin, xmax, ymin, ymax = coords_to_bndbox(x, y, w, h, cell_x, cell_y, img_width, img_height, s)

                # get class name
                class_index = np.argmax(label_tensor[cell_y, cell_x, 10:])
                class_name = INDEX_TO_CLASS_NAME[class_index]

                # add the object the objects list
                obj = {'name': class_name, 'bndbox': [xmin, xmax, ymin, ymax]}
                objects.append(obj)

    label = {
        "image-size": {"depth": img_depth, "width": img_width, "height": img_height},
        "objects": objects
    }

    return label

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import zipfile
    from data_utils import open_example_from_zip, label_image, IMAGES_ZIP_PATH

    with zipfile.ZipFile(IMAGES_ZIP_PATH, 'r') as images_zip:
        img, label = open_example_from_zip(images_zip, "JPEG/2011_004301.jpg")
        print(type(img))
        print(img.shape)
        print(label)

        img = preprocess_image(img)
        label_tensor = preprocess_label(label)
        resized_label = tensor_to_label(label_tensor, img.shape[1], img.shape[0], img.shape[2])

        img = label_image(img, resized_label)
        plt.imshow(img)
        plt.show()