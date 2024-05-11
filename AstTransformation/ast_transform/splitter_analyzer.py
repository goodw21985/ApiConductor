import ast

from ast_transform import astor_fork
from . import scope_analyzer

# This pass is used to build concurrency groups and divide code
# into the various groups.  and to create the DAG.
class CriticalNodeDepenencyGroup:
    def __init__(self):
        self.node_dependencies = set([])
        self.group_dependencies = set([])
        self.recursive_group_dependencies = set([])
        self.grouped_critical_nodes = set([])
        self.triggers = set([])
        self.is_aggregation_group = False
        self.name = ""

    def recursive_set(self, node):
        if self != node:
            self.recursive_group_dependencies.add(node)
        for child in node.group_dependencies:
            self.recursive_set(child)


class SplitterAnalyzer(scope_analyzer.ScopeAnalyzer):
    def __init__(self, copy):
        self.pass_name = "splitter"
        super().__init__(copy)
        self.concurrency_groups = []
        self.critical_node_to_group = {}
        self.aggregated = {}

    def create_concurrency_groups(self):
        groups = {}
        agg_groups = {}
        for critical_node in self.critical_nodes:
            groups[critical_node] = CriticalNodeDepenencyGroup()
        for critical_node in self.critical_nodes:
            nodec = self.node_lookup[critical_node]
            for dependent in nodec.dependency:
                groups[dependent].node_dependencies.add(critical_node)
            groups[critical_node].grouped_critical_nodes.add(critical_node)

        # group multiple critical nodes if they share the same dependency
        grouped_list = []
        for critical_node in self.critical_nodes:
            item = groups[critical_node]
            agg_group = None
            if critical_node in self.critical_nodes_if_groups:
                agg_group_name = "G_"+ self.critical_nodes_if_groups[critical_node]
                if agg_group_name not in agg_groups:
                    agg_groups[agg_group_name]=CriticalNodeDepenencyGroup()
                agg_group = agg_groups[agg_group_name]
                agg_group.name = agg_group_name
                agg_group.is_aggregation_group = True

            ingroup = None
            for item2 in grouped_list:
                if item.node_dependencies == item2.node_dependencies:
                    ingroup = item2
                    break

            if ingroup:
                ingroup.grouped_critical_nodes.add(critical_node)
                self.critical_node_to_group[critical_node] = ingroup
            else:
                item.name = "G" + str(len(grouped_list))
                grouped_list.append(item)
                self.critical_node_to_group[critical_node] = item
                if agg_group:
                    agg_group.group_dependencies.add(item)
                    self.aggregated[item]=agg_group

        for group in grouped_list:
            for node_dependency in group.node_dependencies:
                group_dependency = self.critical_node_to_group[node_dependency]
                if group_dependency in self.aggregated:
                    group_dependency2=self.aggregated[group_dependency]
                    group.group_dependencies.add(group_dependency2)
                elif group_dependency not in group.group_dependencies:
                    group.group_dependencies.add(group_dependency)

        for agg_group in agg_groups.values():
            grouped_list.append(agg_group)

            
        for group in grouped_list:
            group.recursive_set(group)
            for dependent in group.group_dependencies:
                dependent.triggers.add(group)
          #      if len(dependent.triggers) > 1:
          #          raise ValueError("group can only trigger one group")

        self.concurrency_groups = grouped_list

    def assign_nodes_tocreate_concurrency_groups(self):
        for node in self.node_lookup.keys():
            nodec = self.node_lookup[node]
            groups = []
            for c in nodec.dependency:
                g = self.critical_node_to_group[c]
                if g not in groups:
                    groups.append(g)

            trimmed_groups = []
            for g in groups:
                s = " ".join([item.name for item in g.recursive_group_dependencies])
                isCovered = False
                for g2 in groups:
                    if g2 != g and g2 in g.recursive_group_dependencies:
                        isCovered = True
                if not isCovered:
                    trimmed_groups.append(g)

            if not trimmed_groups:
                trimmed_groups.append(self.concurrency_groups[-1])

            if len(trimmed_groups) > 1:
                raise ValueError
            
            aggregated=None
            if isinstance(node, ast.Assign):
                if node.value in self.critical_nodes_if_groups:
                    critical_node_group = self.critical_node_to_group[node.value]
                    aggregated = self.aggregated[critical_node_group]
            
            if node in self.critical_nodes:
                nodec.assigned_concurrency_group = self.critical_node_to_group[node]
            elif aggregated:
                nodec.assigned_concurrency_group = aggregated
            else:
                nodec.assigned_concurrency_group = trimmed_groups[0]
            


def Scan(tree, parent=None):
    analyzer = SplitterAnalyzer(parent)
    analyzer.create_concurrency_groups()
    analyzer.assign_nodes_tocreate_concurrency_groups()
    return analyzer
