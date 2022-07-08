function wrapper_sm(file)

myVars = {'K','Ct','reducedK','offset'};
data = load(file,myVars{:});
offset = data.offset;
K_orig = data.K; % original cost matrix

Ct = data.Ct;
[n1,n2] = size(Ct);
K = - data.reducedK;
num_matches = nnz(Ct);

[nodes,labels] = NodesAndLabels(Ct);

tstart = tic;
fprintf('Start optimization: \n')
fprintf('Model: n1: %g n2: %g \n', n1, n2)

%[sol, v] = spectral_matching_1(K, labels, nodes)
sol = my_spectral_matching(K, labels, nodes)

X = zeros(size(Ct));
%%% Cost matrix for LAP
for i = 1:n1
    f = find(nodes == i);
    X(i, labels(f)) = sol(f);
end

X = discretisationMatching_hungarian(full(X),Ct);

curr_score = X(:)' * K_orig * X(:);
fprintf('time: %f ',toc(tstart))
fprintf('upper_bound: %f ', full(curr_score)+cast(offset,'like',full(curr_score)))
indices = 1:n2;
matching = reshape(X,size(Ct))*indices';
fprintf('labeling: [')
fprintf('%g,',matching(1:end-1))
fprintf('%g] \n',matching(end))


function [v] = my_spectral_matching(M, labels, nodes)

minRatio = eps;

v = ones(length(nodes),1);

v = v/norm(v);

iterClimb = 30;

nNodes = max(nodes);

nLabels = max(labels);

%% compute the first eigenvector (iterative power method)

for i = 1:iterClimb

  v = M*v;

  v = v/norm(v);

end

%% make v double stochastic

aux = v;

v0 = aux;
v1 = aux;

for k = 1:20

    for j = 1:nNodes

        f = find(nodes == j);

        v1(f) = v0(f)/(sum(v0(f))+eps);

    end

    for j = 1:nLabels

        f = find(labels == j);

        v0(f) = v1(f)/(sum(v1(f))+eps);

    end

end

v = (v1+v0)/2;

v = v/norm(v);
