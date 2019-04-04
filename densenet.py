import torchvision.models as models
from torch import nn
import torch.nn.functional as F
from torch.nn.modules.linear import Linear
import torch


def average_cross_entropy(output, label):
    """
    :param output: Tensor of shape batchSize x Nclasses
    :param label: Tensor of shape batchSize x Nclasses
    :return: Sum of the per class entropies
    """
    loss = torch.zeros(1, requires_grad=False)
    if torch.cuda.is_available():
        loss = loss.cuda()

    cross_entropy = F.binary_cross_entropy
    for i in range(output.size()[1]):
        loss += cross_entropy(output[:, i], label[:, i])

    return loss


def add_dropout_rec(module, p):
    if isinstance(module, nn.modules.conv.Conv2d) or isinstance(module, nn.modules.Linear):
        return nn.Sequential(module, nn.Dropout(p))
    for name in module._modules.keys():
        module._modules[name] = add_dropout_rec(module._modules[name], p=p)

    return module


def add_dropout(net, p=0.1):
    for name in net.features._modules.keys():
        if name != "conv0":
            net.features._modules[name] = add_dropout_rec(net.features._modules[name], p=p)
    net.classifier = add_dropout_rec(net.classifier, p=p)
    return net


class DenseNet(nn.Module):
    """
    see https://github.com/pytorch/vision/blob/master/torchvision/models/densenet.py
    """
    def __init__(self, out_features=14, in_features=1024):
        super(DenseNet, self).__init__()
        net = models.densenet121(pretrained=True)
        self.features = net.features
        self.classifier = nn.Sequential(Linear(in_features=in_features, out_features=out_features), nn.Sigmoid())

    def forward(self, x):
        activations = []
        for feat in self.features:
            x = feat(x)
            activations.append(x)

        out = F.relu(x, inplace=True)
        activations.append(out)
        out = F.avg_pool2d(out, kernel_size=7, stride=1)
        # out = F.max_pool2d(out, kernel_size=14, stride=1)
        out = out.view(x.size(0), -1)
        out = self.classifier(out)
        activations.append(out)
        return activations


class DenseNet121(nn.Module):
    """Model modified.
    The architecture of our model is the same as standard DenseNet121
    except the classifier layer which has an additional sigmoid function.
    """
    def __init__(self, out_size):
        super(DenseNet121, self).__init__()
        self.densenet121 = models.densenet121(pretrained=True)
        num_ftrs = self.densenet121.classifier.in_features
        self.densenet121.classifier = nn.Sequential(
            nn.Linear(num_ftrs, out_size),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.densenet121(x)
        return x


def load_dictionary(saved_model_path, map_location=None):
    """
    Used to load state_dict from the repo https://github.com/arnoweng/CheXNet
    :return: dict of the weights to be loaded
    """
    if map_location == 'cpu':
        checkpoint = torch.load(saved_model_path, map_location='cpu')
    else:
        checkpoint = torch.load(saved_model_path)

    keys = checkpoint['state_dict'].copy().keys()
    for key in keys:
        if "norm.1" in key:
            checkpoint['state_dict'][key[7:].replace("norm.1", "norm1")] = checkpoint['state_dict'].pop(key)
        elif "norm.2" in key:
            checkpoint['state_dict'][key[7:].replace("norm.2", "norm2")] = checkpoint['state_dict'].pop(key)
        elif "conv.1" in key:
            checkpoint['state_dict'][key[7:].replace("conv.1", "conv1")] = checkpoint['state_dict'].pop(key)
        elif "conv.2" in key:
            checkpoint['state_dict'][key[7:].replace("conv.2", "conv2")] = checkpoint['state_dict'].pop(key)
        else:
            checkpoint['state_dict'][key[7:]] = checkpoint['state_dict'].pop(key)

    return checkpoint['state_dict']


if __name__ == "__main__":
    pass
