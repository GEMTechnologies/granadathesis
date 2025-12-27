#!/usr/bin/env python3
"""
Citation Network Analysis

Build and analyze citation networks to:
- Find highly cited papers
- Discover paper clusters
- Track research lineage
- Identify seminal works
"""

import networkx as nx
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict
import json
from pathlib import Path


class CitationNetwork:
    """Build and analyze citation networks."""
    
    def __init__(self):
        """Initialize citation network."""
        self.graph = nx.DiGraph()  # Directed graph: A -> B means A cites B
        self.paper_metadata = {}
    
    def add_paper(self, paper: Dict[str, Any]):
        """
        Add paper to network.
        
        Args:
            paper: Paper dictionary with metadata
        """
        paper_id = paper.get("doi") or paper.get("title")
        
        # Add node
        self.graph.add_node(paper_id)
        
        # Store metadata
        self.paper_metadata[paper_id] = {
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "year": paper.get("year"),
            "citations": paper.get("citations", 0),
            "venue": paper.get("venue", ""),
            "source": paper.get("source", "")
        }
    
    def add_citation(self, citing_paper_id: str, cited_paper_id: str):
        """
        Add citation edge.
        
        Args:
            citing_paper_id: Paper that cites
            cited_paper_id: Paper being cited
        """
        self.graph.add_edge(citing_paper_id, cited_paper_id)
    
    def get_most_cited(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Get most cited papers in network.
        
        Args:
            top_n: Number of papers to return
            
        Returns:
            List of (paper_id, citation_count) tuples
        """
        # In-degree = number of papers citing this paper
        in_degrees = dict(self.graph.in_degree())
        
        # Sort by citation count
        sorted_papers = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_papers[:top_n]
    
    def get_influential_papers(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Get most influential papers using PageRank.
        
        Args:
            top_n: Number of papers to return
            
        Returns:
            List of (paper_id, pagerank_score) tuples
        """
        if len(self.graph) == 0:
            return []
        
        try:
            pagerank = nx.pagerank(self.graph)
            sorted_papers = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
            return sorted_papers[:top_n]
        except:
            return []
    
    def find_communities(self) -> List[Set[str]]:
        """
        Find communities/clusters of related papers.
        
        Returns:
            List of paper ID sets (communities)
        """
        if len(self.graph) == 0:
            return []
        
        # Convert to undirected for community detection
        undirected = self.graph.to_undirected()
        
        try:
            # Use Louvain community detection
            from networkx.algorithms import community
            communities = community.greedy_modularity_communities(undirected)
            return [set(c) for c in communities]
        except:
            return []
    
    def get_citation_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """
        Find citation path between two papers.
        
        Args:
            source_id: Starting paper
            target_id: Target paper
            
        Returns:
            List of paper IDs forming the path, or None
        """
        try:
            path = nx.shortest_path(self.graph, source_id, target_id)
            return path
        except nx.NetworkXNoPath:
            return None
    
    def get_related_papers(self, paper_id: str, max_distance: int = 2) -> Set[str]:
        """
        Find papers related by citations.
        
        Args:
            paper_id: Paper to find related papers for
            max_distance: Maximum citation distance
            
        Returns:
            Set of related paper IDs
        """
        if paper_id not in self.graph:
            return set()
        
        related = set()
        
        # Papers this paper cites (out-neighbors)
        for cited in self.graph.successors(paper_id):
            related.add(cited)
            
            # Papers cited by those papers (distance 2)
            if max_distance >= 2:
                for cited2 in self.graph.successors(cited):
                    related.add(cited2)
        
        # Papers that cite this paper (in-neighbors)
        for citing in self.graph.predecessors(paper_id):
            related.add(citing)
            
            # Papers that cite those papers (distance 2)
            if max_distance >= 2:
                for citing2 in self.graph.predecessors(citing):
                    related.add(citing2)
        
        # Remove the original paper
        related.discard(paper_id)
        
        return related
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get network statistics."""
        stats = {
            "total_papers": self.graph.number_of_nodes(),
            "total_citations": self.graph.number_of_edges(),
            "avg_citations_per_paper": 0,
            "max_citations": 0,
            "connected_components": 0,
            "density": 0
        }
        
        if stats["total_papers"] > 0:
            stats["avg_citations_per_paper"] = stats["total_citations"] / stats["total_papers"]
            
            # Max citations
            in_degrees = dict(self.graph.in_degree())
            if in_degrees:
                stats["max_citations"] = max(in_degrees.values())
            
            # Connected components (undirected)
            undirected = self.graph.to_undirected()
            stats["connected_components"] = nx.number_connected_components(undirected)
            
            # Density
            stats["density"] = nx.density(self.graph)
        
        return stats
    
    def export_to_json(self, output_path: Path):
        """Export network to JSON."""
        data = {
            "nodes": [
                {
                    "id": node,
                    "metadata": self.paper_metadata.get(node, {})
                }
                for node in self.graph.nodes()
            ],
            "edges": [
                {"source": u, "target": v}
                for u, v in self.graph.edges()
            ],
            "statistics": self.get_statistics()
        }
        
        output_path.write_text(json.dumps(data, indent=2))
    
    def export_to_gexf(self, output_path: Path):
        """Export network to GEXF format (for Gephi visualization)."""
        nx.write_gexf(self.graph, str(output_path))


def build_network_from_papers(papers: List[Dict[str, Any]]) -> CitationNetwork:
    """
    Build citation network from paper list.
    
    Args:
        papers: List of paper dictionaries
        
    Returns:
        CitationNetwork object
    """
    network = CitationNetwork()
    
    # Add all papers
    for paper in papers:
        network.add_paper(paper)
    
    # TODO: Add citation edges
    # This requires fetching reference lists from APIs
    # For now, we can use citation counts as a proxy
    
    return network


# Example usage
def example_analysis():
    """Example citation network analysis."""
    # Sample papers
    papers = [
        {
            "title": "Attention Is All You Need",
            "doi": "10.1234/transformer",
            "authors": ["Vaswani et al."],
            "year": 2017,
            "citations": 50000,
            "venue": "NeurIPS"
        },
        {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "doi": "10.1234/bert",
            "authors": ["Devlin et al."],
            "year": 2019,
            "citations": 30000,
            "venue": "NAACL"
        }
    ]
    
    # Build network
    network = build_network_from_papers(papers)
    
    # Add citation (BERT cites Transformer)
    network.add_citation("10.1234/bert", "10.1234/transformer")
    
    # Analyze
    print("Network Statistics:")
    stats = network.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nMost Cited Papers:")
    for paper_id, count in network.get_most_cited(5):
        metadata = network.paper_metadata.get(paper_id, {})
        print(f"  {metadata.get('title', paper_id)}: {count} citations")


if __name__ == "__main__":
    example_analysis()
