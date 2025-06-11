import numpy as np
from PIL import Image, ImageDraw


def classifications_to_rails(clf, classes):
    limit_idx = np.where(clf == classes)[1]
    limit_idx = limit_idx.min() if limit_idx.size > 0 else clf.shape[1]

    switched_idx = np.where(clf[0, :] >= clf[1, :])[0]
    switched_idx = switched_idx[0] if switched_idx.size > 0 else clf.shape[1]

    crop_idx = min(limit_idx, switched_idx)
    xrails = clf[:, :crop_idx] / (classes - 1)
    yrails = np.linspace(1, 0, clf.shape[1])[:crop_idx]
    rails = [np.column_stack((xrails[i, :], yrails)) for i in range(xrails.shape[0])]

    return np.array(rails)

def regression_to_rails(traj, ylim):
    limit_idx = round(ylim * traj.shape[1])

    switched_idx = np.where(traj[0, :] >= traj[1, :])[0]
    switched_idx = switched_idx[0] if switched_idx.size > 0 else traj.shape[1]

    crop_idx = min(limit_idx, switched_idx)
    xrails = np.clip(traj[:, :crop_idx], 0, 1)
    yrails = np.linspace(1, 0, traj.shape[1])[:crop_idx]
    rails = [np.column_stack((xrails[i, :], yrails)) for i in range(xrails.shape[0])]

    return np.array(rails)

def scale_rails(rails, crop_coords, img_shape):
    if crop_coords is not None:
        width = crop_coords[2] - crop_coords[0]
        height = crop_coords[3] - crop_coords[1]
        rails[:, :, 0] = rails[:, :, 0] * width + crop_coords[0]
        rails[:, :, 1] = rails[:, :, 1] * height + crop_coords[1]
    else:
        rails[:, :, 0] *= img_shape[0] - 1
        rails[:, :, 1] *= img_shape[1] - 1
    return rails

def rails_to_mask(rails, mask_shape):
    left_rail, right_rail = rails

    if not left_rail or not right_rail:
        return np.zeros(mask_shape[::-1], dtype=np.uint8)

    mask = Image.new("L", mask_shape, 0)
    draw = ImageDraw.Draw(mask)
    points = left_rail + right_rail[::-1]
    draw.polygon([tuple(xy) for xy in points], fill=255)

    return mask

def scale_mask(mask, crop_coords, img_shape):
    if crop_coords is not None:
        xleft, ytop, xright, ybottom = crop_coords
        mask = mask.resize((xright - xleft + 1, ybottom - ytop + 1), Image.NEAREST)
        rescaled_mask = Image.new("L", img_shape, 0)
        rescaled_mask.paste(mask, (xleft, ytop))
    else:
        rescaled_mask = mask.resize(img_shape, Image.NEAREST)
    return rescaled_mask
