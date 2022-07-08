function [X] = FlatUniform(Ct)

  [n1,n2] = size(Ct);
  %%% Initialization: flat uniform
  X = ones(n1,n2);
  X(Ct == 0) = 0;
  X = X ./ norm(X(:));
