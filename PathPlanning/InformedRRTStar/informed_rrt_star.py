"""
Informed RRT* path planning

author: Karan Chawla
        Atsushi Sakai(@Atsushi_twi)

Reference: Informed RRT*: Optimal Sampling-based Path planning Focused via
Direct Sampling of an Admissible Ellipsoidal Heuristichttps://arxiv.org/pdf/1404.2334.pdf

"""

import copy
import math
import random

import matplotlib.pyplot as plt
import numpy as np

show_animation = True


class InformedRRTStar:

    def __init__(self, start, goal,
                 obstacleList, randArea,
                 expandDis=0.5, goalSampleRate=10, maxIter=200):

        self.start = Node(start[0], start[1])
        self.goal = Node(goal[0], goal[1])
        self.min_rand = randArea[0]
        self.max_rand = randArea[1]
        self.expand_dis = expandDis
        self.goal_sample_rate = goalSampleRate
        self.max_iter = maxIter
        self.obstacle_list = obstacleList
        self.node_list = None

    def informed_rrt_star_search(self, animation=True):

        self.node_list = [self.start]
        # max length we expect to find in our 'informed' sample space, starts as infinite
        cBest = float('inf')
        pathLen = float('inf')
        solutionSet = set()
        path = None

        # Computing the sampling space
        cMin = math.sqrt(pow(self.start.x - self.goal.x, 2)
                         + pow(self.start.y - self.goal.y, 2))
        xCenter = np.array([[(self.start.x + self.goal.x) / 2.0],
                            [(self.start.y + self.goal.y) / 2.0], [0]])
        a1 = np.array([[(self.goal.x - self.start.x) / cMin],
                       [(self.goal.y - self.start.y) / cMin], [0]])

        etheta = math.atan2(a1[1], a1[0])
        # first column of idenity matrix transposed
        id1_t = np.array([1.0, 0.0, 0.0]).reshape(1, 3)
        M = a1 @ id1_t
        U, S, Vh = np.linalg.svd(M, True, True)
        C = np.dot(np.dot(U, np.diag(
            [1.0, 1.0, np.linalg.det(U) * np.linalg.det(np.transpose(Vh))])), Vh)

        for i in range(self.max_iter):
            # Sample space is defined by cBest
            # cMin is the minimum distance between the start point and the goal
            # xCenter is the midpoint between the start and the goal
            # cBest changes when a new path is found

            rnd = self.informed_sample(cBest, cMin, xCenter, C)
            nind = self.get_nearest_list_index(self.node_list, rnd)
            nearestNode = self.node_list[nind]
            # steer
            theta = math.atan2(rnd[1] - nearestNode.y, rnd[0] - nearestNode.x)
            newNode = self.get_new_node(theta, nind, nearestNode)
            d = self.line_cost(nearestNode, newNode)

            isCollision = self.collision_check(newNode, self.obstacle_list)
            isCollisionEx = self.check_collision_extend(nearestNode, theta, d)

            if isCollision and isCollisionEx:
                nearInds = self.find_near_nodes(newNode)
                newNode = self.choose_parent(newNode, nearInds)

                self.node_list.append(newNode)
                self.rewire(newNode, nearInds)

                if self.is_near_goal(newNode):
                    solutionSet.add(newNode)
                    lastIndex = len(self.node_list) - 1
                    tempPath = self.get_final_course(lastIndex)
                    tempPathLen = self.get_path_len(tempPath)
                    if tempPathLen < pathLen:
                        path = tempPath
                        cBest = tempPathLen

            if animation:
                self.draw_graph(xCenter=xCenter,
                                cBest=cBest, cMin=cMin,
                                etheta=etheta, rnd=rnd)

        return path

    def choose_parent(self, newNode, nearInds):
        if len(nearInds) == 0:
            return newNode

        dList = []
        for i in nearInds:
            dx = newNode.x - self.node_list[i].x
            dy = newNode.y - self.node_list[i].y
            d = math.sqrt(dx ** 2 + dy ** 2)
            theta = math.atan2(dy, dx)
            if self.check_collision_extend(self.node_list[i], theta, d):
                dList.append(self.node_list[i].cost + d)
            else:
                dList.append(float('inf'))

        minCost = min(dList)
        minInd = nearInds[dList.index(minCost)]

        if minCost == float('inf'):
            print("mincost is inf")
            return newNode

        newNode.cost = minCost
        newNode.parent = minInd

        return newNode

    def find_near_nodes(self, newNode):
        nnode = len(self.node_list)
        r = 50.0 * math.sqrt((math.log(nnode) / nnode))
        dlist = [(node.x - newNode.x) ** 2
                 + (node.y - newNode.y) ** 2 for node in self.node_list]
        nearinds = [dlist.index(i) for i in dlist if i <= r ** 2]
        return nearinds

    def informed_sample(self, cMax, cMin, xCenter, C):
        if cMax < float('inf'):
            r = [cMax / 2.0,
                 math.sqrt(cMax ** 2 - cMin ** 2) / 2.0,
                 math.sqrt(cMax ** 2 - cMin ** 2) / 2.0]
            L = np.diag(r)
            xBall = self.sample_unit_ball()
            rnd = np.dot(np.dot(C, L), xBall) + xCenter
            rnd = [rnd[(0, 0)], rnd[(1, 0)]]
        else:
            rnd = self.sample_free_space()

        return rnd

    @staticmethod
    def sample_unit_ball():
        a = random.random()
        b = random.random()

        if b < a:
            a, b = b, a

        sample = (b * math.cos(2 * math.pi * a / b),
                  b * math.sin(2 * math.pi * a / b))
        return np.array([[sample[0]], [sample[1]], [0]])

    def sample_free_space(self):
        if random.randint(0, 100) > self.goal_sample_rate:
            rnd = [random.uniform(self.min_rand, self.max_rand),
                   random.uniform(self.min_rand, self.max_rand)]
        else:
            rnd = [self.goal.x, self.goal.y]

        return rnd

    @staticmethod
    def get_path_len(path):
        pathLen = 0
        for i in range(1, len(path)):
            node1_x = path[i][0]
            node1_y = path[i][1]
            node2_x = path[i - 1][0]
            node2_y = path[i - 1][1]
            pathLen += math.sqrt((node1_x - node2_x)
                                 ** 2 + (node1_y - node2_y) ** 2)

        return pathLen

    @staticmethod
    def line_cost(node1, node2):
        return math.sqrt((node1.x - node2.x) ** 2 + (node1.y - node2.y) ** 2)

    @staticmethod
    def get_nearest_list_index(nodes, rnd):
        dList = [(node.x - rnd[0]) ** 2
                 + (node.y - rnd[1]) ** 2 for node in nodes]
        minIndex = dList.index(min(dList))
        return minIndex

    @staticmethod
    def collision_check(newNode, obstacleList):
        for (ox, oy, size) in obstacleList:
            dx = ox - newNode.x
            dy = oy - newNode.y
            d = dx * dx + dy * dy
            if d <= 1.1 * size ** 2:
                return False  # collision

        return True  # safe

    def get_new_node(self, theta, nind, nearestNode):
        newNode = copy.deepcopy(nearestNode)

        newNode.x += self.expand_dis * math.cos(theta)
        newNode.y += self.expand_dis * math.sin(theta)

        newNode.cost += self.expand_dis
        newNode.parent = nind
        return newNode

    def is_near_goal(self, node):
        d = self.line_cost(node, self.goal)
        if d < self.expand_dis:
            return True
        return False

    def rewire(self, newNode, nearInds):
        n_node = len(self.node_list)
        for i in nearInds:
            nearNode = self.node_list[i]

            d = math.sqrt((nearNode.x - newNode.x) ** 2
                          + (nearNode.y - newNode.y) ** 2)

            scost = newNode.cost + d

            if nearNode.cost > scost:
                theta = math.atan2(newNode.y - nearNode.y,
                                   newNode.x - nearNode.x)
                if self.check_collision_extend(nearNode, theta, d):
                    nearNode.parent = n_node - 1
                    nearNode.cost = scost

    def check_collision_extend(self, nearNode, theta, d):
        tmpNode = copy.deepcopy(nearNode)

        for i in range(int(d / self.expand_dis)):
            tmpNode.x += self.expand_dis * math.cos(theta)
            tmpNode.y += self.expand_dis * math.sin(theta)
            if not self.collision_check(tmpNode, self.obstacle_list):
                return False

        return True

    def get_final_course(self, lastIndex):
        path = [[self.goal.x, self.goal.y]]
        while self.node_list[lastIndex].parent is not None:
            node = self.node_list[lastIndex]
            path.append([node.x, node.y])
            lastIndex = node.parent
        path.append([self.start.x, self.start.y])
        return path

    def draw_graph(self, xCenter=None, cBest=None, cMin=None, etheta=None, rnd=None):

        plt.clf()
        if rnd is not None:
            plt.plot(rnd[0], rnd[1], "^k")
            if cBest != float('inf'):
                self.plot_ellipse(xCenter, cBest, cMin, etheta)

        for node in self.node_list:
            if node.parent is not None:
                if node.x or node.y is not None:
                    plt.plot([node.x, self.node_list[node.parent].x], [
                        node.y, self.node_list[node.parent].y], "-g")

        for (ox, oy, size) in self.obstacle_list:
            plt.plot(ox, oy, "ok", ms=30 * size)

        plt.plot(self.start.x, self.start.y, "xr")
        plt.plot(self.goal.x, self.goal.y, "xr")
        plt.axis([-2, 15, -2, 15])
        plt.grid(True)
        plt.pause(0.01)

    @staticmethod
    def plot_ellipse(xCenter, cBest, cMin, etheta):  # pragma: no cover

        a = math.sqrt(cBest ** 2 - cMin ** 2) / 2.0
        b = cBest / 2.0
        angle = math.pi / 2.0 - etheta
        cx = xCenter[0]
        cy = xCenter[1]

        t = np.arange(0, 2 * math.pi + 0.1, 0.1)
        x = [a * math.cos(it) for it in t]
        y = [b * math.sin(it) for it in t]
        R = np.array([[math.cos(angle), math.sin(angle)],
                      [-math.sin(angle), math.cos(angle)]])
        fx = R @ np.array([x, y])
        px = np.array(fx[0, :] + cx).flatten()
        py = np.array(fx[1, :] + cy).flatten()
        plt.plot(cx, cy, "xc")
        plt.plot(px, py, "--c")


class Node:

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.cost = 0.0
        self.parent = None


def main():
    print("Start informed rrt star planning")

    # create obstacles
    obstacleList = [
        (5, 5, 0.5),
        (9, 6, 1),
        (7, 5, 1),
        (1, 5, 1),
        (3, 6, 1),
        (7, 9, 1)
    ]

    # Set params
    rrt = InformedRRTStar(start=[0, 0], goal=[5, 10],
                          randArea=[-2, 15], obstacleList=obstacleList)
    path = rrt.informed_rrt_star_search(animation=show_animation)
    print("Done!!")

    # Plot path
    if show_animation:
        rrt.draw_graph()
        plt.plot([x for (x, y) in path], [y for (x, y) in path], '-r')
        plt.grid(True)
        plt.pause(0.01)
        plt.show()


if __name__ == '__main__':
    main()
