function [nodes,labels] = NodesAndLabels(Ct)
  [n1,n2] = size(Ct);
  %%%% Nodes
  vec_nodes = 1:n1;
  mat_nodes = diag(vec_nodes) * ones(n1,n2);
  nodes_help = Ct .* mat_nodes;
  nodes = nodes_help(find(Ct));
  %%%% Labels
  vec_labels = 1:n2;
  mat_labels = ones(n1,n2) * diag(vec_labels);
  labels_help = Ct .* mat_labels;
  labels = labels_help(find(Ct));
