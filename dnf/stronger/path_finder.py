# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'


class PathFinder:
    # def __init__(self, rows, cols, start_pos, target_pos):
    def __init__(self, rows, cols, target_pos):
        self.rows = rows
        self.cols = cols
        self.target_pos = target_pos
        self.visited = {}  # 记录已访问格子的联通方向
        self.path_stack = []  # 用于回溯的路径栈
        self.visited_diff_cnt = {}

    def get_next_direction(self, current_pos, directions):
        """
        核心决策逻辑：全局搜索所有未探索方向，选择最优路径
        :param current_pos: 当前坐标 (row, col)
        :param directions: 当前坐标的可用移动方向列表
        :return: 推荐的移动方向
        """
        # 更新访问记录
        if current_pos not in self.visited:
            self.visited[current_pos] = directions
            # 移除路径栈中可能存在的冗余记录
            while self.path_stack and self.path_stack[-1] != current_pos:
                self.path_stack.pop()
            self.path_stack.append(current_pos)
        else:
            # 更新联通方向
            if not self.visited[current_pos]:
                self.visited[current_pos] = directions
            else:
                if self.visited[current_pos] != directions:
                    if current_pos not in self.visited_diff_cnt:
                        self.visited_diff_cnt[current_pos] = 0
                    self.visited_diff_cnt[current_pos] = self.visited_diff_cnt[current_pos] + 1

                    if self.visited_diff_cnt[current_pos] > 8:
                        self.visited_diff_cnt[current_pos] = 0
                        self.visited[current_pos] = directions
        # 收集全局候选方向
        candidates = self._collect_all_candidates()

        # 优先处理全局最优候选
        if candidates:
            closest = min(candidates, key=lambda pos: self._manhattan(pos, self.target_pos))
            path = self._bfs_to_candidate(current_pos, closest)
            if path and len(path) > 1:
                return self._get_direction(current_pos, path[1])

        # 处理当前格子未探索方向（当全局候选不可达时）
        unexplored = [d for d in directions
                      if self._get_next_pos(current_pos, d) not in self.visited]
        if unexplored:
            best_dir = self._select_best_direction(current_pos, unexplored)
            return best_dir

        # 尝试直达终点
        path_to_target = self._bfs(current_pos)
        if path_to_target and len(path_to_target) > 1:
            return self._get_direction(current_pos, path_to_target[1])

        # 最后进行回溯
        return self._backtrack(current_pos)

    def _collect_all_candidates(self):
        """收集所有已知的未探索相邻格子"""
        candidates = set()
        for pos in self.visited:
            for direction in self.visited[pos]:
                next_pos = self._get_next_pos(pos, direction)
                if next_pos not in self.visited:
                    candidates.add(next_pos)
        return list(candidates)

    def _bfs_to_candidate(self, start_pos, target_candidate):
        """BFS寻找通往特定候选的路径（允许最后一步到达未访问格子）"""
        from collections import deque
        visited = set()
        queue = deque([(start_pos, [])])
        visited.add(start_pos)

        while queue:
            current, path = queue.popleft()

            # 检查当前节点是否可以直接到达候选
            if current in self.visited:
                for d in self.visited[current]:
                    next_pos = self._get_next_pos(current, d)
                    if next_pos == target_candidate:
                        return path + [current, next_pos]

            # 继续探索已知区域
            if current not in self.visited:
                continue
            for d in self.visited[current]:
                next_p = self._get_next_pos(current, d)
                if next_p in self.visited and next_p not in visited:
                    visited.add(next_p)
                    queue.append((next_p, path + [current]))

        return None

    def _find_closest_candidate(self):
        """找到曼哈顿距离最近的未探索候选"""
        closest = None
        min_dist = float('inf')
        for candidate in self.unexplored_candidates:
            dist = self._manhattan(candidate, self.target_pos)
            if dist < min_dist:
                min_dist = dist
                closest = candidate
        return closest

    def _bfs_to_candidate(self, start_pos, target_candidate):
        """BFS寻找通往特定候选的路径"""
        from collections import deque
        visited = set()
        queue = deque([(start_pos, [])])
        visited.add(start_pos)

        while queue:
            current, path = queue.popleft()
            if current == target_candidate:
                return path + [current]
            if current not in self.visited:
                continue
            for d in self.visited[current]:
                next_pos = self._get_next_pos(current, d)
                if next_pos == target_candidate or next_pos in self.visited:
                    if next_pos not in visited:
                        visited.add(next_pos)
                        queue.append((next_pos, path + [current]))
        return None

    def _backtrack(self, current_pos):
        """回溯到最近的未完全探索的格子"""
        while self.path_stack:
            self.path_stack.pop()
            if not self.path_stack:
                return None
            previous_pos = self.path_stack[-1]
            # 检查前一个格子是否有未探索方向
            if any(self._get_next_pos(previous_pos, d) not in self.visited
                   for d in self.visited.get(previous_pos, [])):
                return self._get_direction(current_pos, previous_pos)
        return None

    def _get_next_pos(self, pos, direction):
        """根据方向计算下一个坐标"""
        row, col = pos
        if direction == 'UP':
            return (row - 1, col)
        elif direction == 'DOWN':
            return (row + 1, col)
        elif direction == 'LEFT':
            return (row, col - 1)
        elif direction == 'RIGHT':
            return (row, col + 1)
        else:
            raise ValueError("无效方向")

    def _select_best_direction(self, current_pos, directions):
        """选择曼哈顿距离最近的方向"""
        min_dist = float('inf')
        best_dir = None
        for d in directions:
            next_pos = self._get_next_pos(current_pos, d)
            dist = self._manhattan(next_pos, self.target_pos)
            if dist < min_dist:
                min_dist = dist
                best_dir = d
        return best_dir

    def _manhattan(self, pos1, pos2):
        """计算曼哈顿距离"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _bfs(self, start_pos):
        """BFS寻找已知区域内的最短路径"""
        
        if start_pos == self.target_pos:
            return [start_pos]
        
        from collections import deque
        if self.target_pos not in self.visited:
            return None  # 终点未被探索过

        visited_bfs = set()
        queue = deque()
        queue.append((start_pos, []))
        visited_bfs.add(start_pos)

        while queue:
            current, path = queue.popleft()
            if current == self.target_pos:
                return path + [current]

            if current not in self.visited:
                continue

            for d in self.visited[current]:
                next_pos = self._get_next_pos(current, d)
                if next_pos in self.visited and next_pos not in visited_bfs:
                    visited_bfs.add(next_pos)
                    queue.append((next_pos, path + [current]))
        return None

    def _get_direction(self, current_pos, next_pos):
        """根据当前坐标和目标坐标确定移动方向"""
        curr_row, curr_col = current_pos
        next_row, next_col = next_pos

        if next_row < curr_row:
            return 'UP'
        elif next_row > curr_row:
            return 'DOWN'
        elif next_col < curr_col:
            return 'LEFT'
        elif next_col > curr_col:
            return 'RIGHT'
        else:
            return None
