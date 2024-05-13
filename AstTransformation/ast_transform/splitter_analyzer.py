import ast

from ast_transform import astor_fork
from . import scope_analyzer

# This pass is used to build concurrency groups and divide code
# into the various groups.  and to create the DAG.
#
# This pass does not walk the ast, but walk the ast nodes via the nod cross reference
#
# A concurrency group is made from one or more critical nodes (if two critical nodes share all dependencies, they are grouped)
# There is a final concurrency group created from a return statement or otherwise, which does all processing needed after all other
# critical nodes are completed, and so the return statement is also considered a critical node.  Thus there always will be at least
# one concurrency group.
#
# aggregate concurrency groups are created when more than one critical nodes write to a common variable and are mutually exclusive
# due to being in different branches of an if statement.   The aggregate group waits for all the values to be complete (or not) and
# then triggers further dependencies.


class CriticalNodeDepenencyGroup:
    def __init__(self):
        self.depends_on_critical_node = set([])
        self.depends_on_group = set([])
        self.recursive_depends_on_group = set([])
        self.grouped_critical_nodes = set([])
        self.triggers = set([])
        self.is_aggregation_group = False
        self.name = ""
        self.stack=[]

    def recursive_set(self, node):        
        if self != node:
            self.recursive_depends_on_group.add(node)
        if node in self.stack:
            return
        self.stack.append(node)
        for child in node.depends_on_group:
            self.recursive_set(child)
        
        self.stack.pop()


class SplitterAnalyzer(scope_analyzer.ScopeAnalyzer):
    def __init__(self, copy):
        self.pass_name = "splitter"
        super().__init__(copy)
        self.concurrency_groups = []
        self.critical_node_to_group = {}
        self.aggregated = {}

    def concurrent_critical_nodes(self):
        return (item for item in self.critical_nodes if item not in self.non_concurrent_critical_nodes)
    
    def create_concurrency_groups(self):
        groups = {}
        agg_groups = {}
        groups_who_use_node={}
        for critical_node in self.concurrent_critical_nodes():
            groups[critical_node] = CriticalNodeDepenencyGroup()
        for critical_node in self.concurrent_critical_nodes():
            nodec = self.node_lookup[critical_node]
            for dependent in nodec.dependency:
                groups[dependent].depends_on_critical_node.add(critical_node)
            groups[critical_node].grouped_critical_nodes.add(critical_node)

        # group multiple critical nodes if they share the same dependency
        grouped_list = []
        for critical_node in self.concurrent_critical_nodes():
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
                if item.depends_on_critical_node == item2.depends_on_critical_node:
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
                item = self.critical_node_to_group[critical_node]
                agg_group.depends_on_group.add(item)
                self.aggregated[item]=agg_group

        for group in grouped_list:
            for node_dependency in group.depends_on_critical_node:
                group_dependency = self.critical_node_to_group[node_dependency]
                if group_dependency in self.aggregated:
                    group_dependency2=self.aggregated[group_dependency]
                    if node_dependency in self.critical_nodes_if_groups:
                        # this is where we patch the agg group to who it targets, in
                        # which we have to trace back the critical node, see what it
                        # triggers, and lookup its group
                        nodec = self.node_lookup[node_dependency]
                        for dependent in nodec.dependency:
                            target_group = self.critical_node_to_group[dependent]
                            target_group.depends_on_group.add(group_dependency2)
                
                group.depends_on_group.add(group_dependency)

        for agg_group in agg_groups.values():
            grouped_list.append(agg_group)

            
        for group in grouped_list:
            group.recursive_set(group)
            for dependent in group.depends_on_group:
                dependent.triggers.add(group)
          #      if len(dependent.triggers) > 1:
          #          raise ValueError("group can only trigger one group")
          
          

        self.concurrency_groups = grouped_list

    def assign_nodes_tocreate_concurrency_groups(self):
        for node in self.node_lookup.keys():
            nodec = self.node_lookup[node]
            groups = []
            for c in nodec.dependency:
                if c not in self.non_concurrent_critical_nodes:
                    g = self.critical_node_to_group[c]
                    if g not in groups:
                        groups.append(g)

            trimmed_groups = []
            for g in groups:
                s = " ".join([item.name for item in g.recursive_depends_on_group])
                isCovered = False
                for g2 in groups:
                    if g2 != g and g2 in g.recursive_depends_on_group:
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
                    if critical_node_group in self.aggregated:
                        aggregated = self.aggregated[critical_node_group]
                    else:
                        pass

            if node in self.concurrent_critical_nodes():
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
